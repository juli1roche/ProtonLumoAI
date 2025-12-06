#!/usr/bin/env python3
# ============================================================================
# EMAIL PROCESSOR - ProtonLumoAI
# Processeur principal avec gestion STARTTLS et Parsing Robuste
# + Executive Summary v1.1.0
# ============================================================================

import os
import time
import signal
import sys
import ssl
import imaplib
import json
from pathlib import Path
from typing import Optional, Set, Dict, List
from datetime import datetime, timedelta
import email.utils
import threading

from loguru import logger
from dotenv import load_dotenv

# Import des modules locaux
try:
    from email_classifier import EmailClassifier
    from email_parser import EmailParser
    from feedback_manager import FeedbackManager
    from important_message_detector import ImportantMessageDetector, ImportantMessage
    from summary_email_reporter import SummaryEmailReporter
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from email_classifier import EmailClassifier
    from email_parser import EmailParser
    from feedback_manager import FeedbackManager
    from important_message_detector import ImportantMessageDetector, ImportantMessage
    from summary_email_reporter import SummaryEmailReporter

# Chargement des variables d'environnement
load_dotenv()

# --- CONFIGURATION ---
PROTON_BRIDGE_HOST = os.getenv("PROTON_BRIDGE_HOST", "127.0.0.1")
PROTON_BRIDGE_PORT = int(os.getenv("PROTON_BRIDGE_PORT", 1143))
PROTON_USERNAME = os.getenv("PROTON_USERNAME")
PROTON_PASSWORD = os.getenv("PROTON_PASSWORD")
POLL_INTERVAL = int(os.getenv("PROTON_LUMO_POLL_INTERVAL", 60))
UNSEEN_ONLY = os.getenv("PROTON_LUMO_UNSEEN_ONLY", "true").lower() == "true"
DRY_RUN = os.getenv("PROTON_LUMO_DRY_RUN", "false").lower() == "true"
MAX_EMAILS_PER_FOLDER = int(os.getenv("PROTON_LUMO_MAX_EMAILS_PER_FOLDER", 100))

# Executive Summary Configuration
SUMMARY_ENABLED = os.getenv("PROTON_LUMO_SUMMARY_ENABLED", "true").lower() == "true"
SUMMARY_HOURS = list(map(int, os.getenv("PROTON_LUMO_SUMMARY_HOURS", "09,13,17").split(",")))
SUMMARY_MIN_SCORE = int(os.getenv("PROTON_LUMO_SUMMARY_MIN_SCORE", "30"))
SUMMARY_FORMAT = os.getenv("PROTON_LUMO_SUMMARY_FORMAT", "email").lower()

# Limites spéciales pour certains dossiers
SPAM_TRASH_LIMIT = 10  # Limite pour Spam/Trash

# Répertoires de données
DATA_DIR = Path(os.getenv("PROTON_LUMO_DATA", "~/ProtonLumoAI/data")).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_FILE = DATA_DIR / "checkpoint.json"


class ProtonMailBox:
    """
    Wrapper IMAP pour ProtonMail Bridge gérant spécifiquement STARTTLS.
    Le Bridge n'utilise pas SSL direct (port 993) mais STARTTLS (port 1143).
    """
    
    def __init__(self, host, port, username, password, timeout=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout or 10
        self.client: Optional[imaplib.IMAP4] = None
        self._existing_folders: Set[str] = set()
        self._connect()
    
    def _connect(self):
        """'Établit la connexion STARTTLS avec ProtonMail Bridge"""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            logger.debug(f"Connexion IMAP à {self.host}:{self.port}...")
            self.client = imaplib.IMAP4(self.host, self.port, timeout=self.timeout)
            
            logger.debug("Envoi de la commande STARTTLS...")
            self.client.starttls(ssl_context=ssl_context)
            
            logger.debug(f"Authentification pour {self.username}...")
            self.client.login(self.username, self.password)
            
            logger.success(f"Connexion établie avec succès ({self.host}:{self.port})")
            self._refresh_folder_cache()
            
        except Exception as e:
            logger.error(f"Échec de la connexion IMAP/STARTTLS : {e}")
            if self.client:
                try:
                    self.client.logout()
                except:
                    pass
            raise

    def _refresh_folder_cache(self):
        """Met à jour le cache des dossiers existants"""
        try:
            status, folders = self.client.list()
            if status == 'OK':
                for folder_bytes in folders:
                    try:
                        folder_raw = folder_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        folder_raw = folder_bytes.decode('latin-1')
                    
                    # ✅ FIX: Parser correctement le format IMAP LIST
                    # Format: (\\Flags) "/" "Nom/Du/Dossier"
                    parts = folder_raw.split('"')
                    if len(parts) >= 3:
                        # Le nom est entre les deux derniers guillemets
                        folder_name = parts[-2]
                        self._existing_folders.add(folder_name)
        except Exception as e:
            logger.warning(f"Erreur lors de la mise à jour du cache des dossiers: {e}")

    def folder_exists(self, folder_path: str) -> bool:
        """Vérifie si un dossier existe"""
        return folder_path in self._existing_folders

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Ferme proprement la connexion"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
            try:
                self.client.logout()
            except:
                pass


class EmailProcessor:
    """Processeur principal orchestrant le tri et l'apprentissage + Executive Summary."""

    def __init__(self):
        self.classifier = EmailClassifier()
        self.parser = EmailParser()
        self.feedback_manager: Optional[FeedbackManager] = None
        self.running = True
        
        # Initialiser le détecteur de messages importants (v1.1.0)
        if SUMMARY_ENABLED:
            self.detector = ImportantMessageDetector()
            self.reporter = None  # Sera initialisé avec la connexion IMAP
            self.last_summary_hour = -1
            logger.info(f"✨ Executive Summary ACTIVÉ - Rapports à: {SUMMARY_HOURS}:00 CET")
        else:
            self.detector = None
            self.reporter = None
        
        # Chargement du checkpoint pour éviter de retraiter les mêmes emails
        self.checkpoint = self._load_checkpoint()
        self.initial_scan_done = self.checkpoint.get('initial_scan_done', False)
        self.last_check: Dict[str, str] = self.checkpoint.get('last_check', {})
        self.processed_emails: Set[str] = set(self.checkpoint.get('processed_emails', []))
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info(f"EmailProcessor démarré [Dry Run: {DRY_RUN}, Unseen Only: {UNSEEN_ONLY}, Max/Folder: {MAX_EMAILS_PER_FOLDER}]")
        if self.initial_scan_done:
            logger.info(f"➡️  Reprise depuis checkpoint: {len(self.processed_emails)} emails déjà traités")

    def _load_checkpoint(self) -> dict:
        """Charge le checkpoint depuis le disque"""
        if CHECKPOINT_FILE.exists():
            try:
                with open(CHECKPOINT_FILE, 'r') as f:
                    data = json.load(f)
                    logger.info(f"✓ Checkpoint chargé: {CHECKPOINT_FILE}")
                    return data
            except Exception as e:
                logger.warning(f"Impossible de charger le checkpoint: {e}")
        return {}

    def _save_checkpoint(self):
        """Sauvegarde le checkpoint sur disque"""
        try:
            checkpoint_data = {
                'initial_scan_done': self.initial_scan_done,
                'last_check': self.last_check,
                'processed_emails': list(self.processed_emails),
                'last_update': datetime.now().isoformat()
            }
            with open(CHECKPOINT_FILE, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            logger.debug(f"✓ Checkpoint sauvegardé: {len(self.processed_emails)} emails traités")
        except Exception as e:
            logger.error(f"Erreur sauvegarde checkpoint: {e}")

    def _signal_handler(self, sig, frame):
        logger.info("Signal d'arrêt reçu. Sauvegarde du checkpoint...")
        self._save_checkpoint()
        logger.info("Fermeture...")
        self.running = False

    def connect_mailbox(self) -> ProtonMailBox:
        """Crée et retourne une instance connectée de ProtonMailBox."""
        if not PROTON_USERNAME or not PROTON_PASSWORD:
            logger.error("Identifiants manquants. Vérifiez votre fichier .env")
            sys.exit(1)
            
        return ProtonMailBox(
            PROTON_BRIDGE_HOST,
            PROTON_BRIDGE_PORT,
            PROTON_USERNAME,
            PROTON_PASSWORD
        )

    def _get_target_folder(self, category: str) -> Optional[str]:
        """Récupère le dossier cible pour une catégorie donnée."""
        if category == "UNKNOWN":
            return None
            
        cat_obj = self.classifier.categories.get(category)
        if cat_obj:
            return cat_obj.folder
        return None

    def ensure_folder_exists(self, mailbox: ProtonMailBox, folder_path: str) -> bool:
        """
        S'assure qu'un dossier existe, le crée récursivement si nécessaire.
        Retourne True si le dossier existe ou a été créé, False en cas d'échec.
        """
        # Vérifier le cache d'abord
        if mailbox.folder_exists(folder_path):
            logger.debug(f"Dossier {folder_path} déjà dans le cache")
            return True
        
        # Créer récursivement
        path_parts = folder_path.split('/')
        current_path = ''
        
        for part in path_parts:
            if current_path:
                current_path += '/'
            current_path += part
            
            if not mailbox.folder_exists(current_path):
                try:
                    logger.debug(f"Création du dossier: {current_path}")
                    mailbox.client.create(f'"{current_path}"')
                    
                    # Attendre un peu pour que le serveur synchronise
                    time.sleep(0.5)
                    
                    # Rafraîchir le cache après création
                    mailbox._refresh_folder_cache()
                    
                    # Vérifier que le dossier a bien été créé
                    if mailbox.folder_exists(current_path):
                        logger.success(f"✓ Dossier créé: {current_path}")
                    else:
                        logger.warning(f"Dossier {current_path} créé mais absent du cache")
                        mailbox._existing_folders.add(current_path)
                        
                except Exception as e:
                    logger.error(f"Impossible de créer le dossier {current_path}: {e}")
                    return False
        
        return True

    def _get_email_date(self, mailbox: ProtonMailBox, email_id: bytes) -> datetime:
        """
        Récupère la date d'un email pour le tri.
        Retourne la date ou datetime.min si erreur.
        """
        try:
            res_flags, flags_data = mailbox.client.fetch(email_id, '(INTERNALDATE)')
            if res_flags == 'OK' and flags_data and flags_data[0]:
                # Parser la date IMAP (format: "DD-Mon-YYYY HH:MM:SS +ZZZZ")
                date_str = flags_data[0].decode('utf-8', errors='ignore')
                # Extraire la date entre guillemets
                import re
                match = re.search(r'"([^"]+)"', date_str)
                if match:
                    date_tuple = email.utils.parsedate_tz(match.group(1))
                    if date_tuple:
                        return datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
        except Exception as e:
            logger.debug(f"Erreur récupération date email: {e}")
        
        return datetime.min

    def _sort_emails_by_date(self, mailbox: ProtonMailBox, email_ids: List[bytes], limit: int) -> List[bytes]:
        """
        Trie les emails par date décroissante et retourne les {limit} plus récents.
        """
        if not email_ids or len(email_ids) <= limit:
            return email_ids
        
        logger.debug(f"Tri de {len(email_ids)} emails par date pour garder les {limit} plus récents...")
        
        # Créer une liste (email_id, date)
        emails_with_dates = []
        for email_id in email_ids:
            date = self._get_email_date(mailbox, email_id)
            emails_with_dates.append((email_id, date))
        
        # Trier par date décroissante (plus récents en premier)
        emails_with_dates.sort(key=lambda x: x[1], reverse=True)
        
        # Retourner seulement les IDs des {limit} plus récents
        recent_emails = [email_id for email_id, _ in emails_with_dates[:limit]]
        
        logger.debug(f"✓ {len(recent_emails)} emails les plus récents sélectionnés")
        return recent_emails

    def _score_and_track_message(self, email_uid: str, from_email: str, subject: str, body: str, category: str, confidence: float) -> None:
        """
        Score le message pour l'Executive Summary et le sauvegarde.
        Called after successful classification.
        """
        if not self.detector:
            return
        
        try:
            # Score le message selon plusieurs critères
            score, breakdown, action_type = self.detector.score_message(
                email_uid, from_email, subject, body, category, confidence
            )
            
            # Si important (score >= seuil), créer et sauvegarder
            if score >= SUMMARY_MIN_SCORE:
                msg = ImportantMessage(
                    message_id=email_uid,
                    from_email=from_email,
                    subject=subject[:100],  # Limiter la longueur
                    score=score,
                    category=category,
                    criteria_breakdown=breakdown,
                    action_type=action_type,
                    status="new",
                    detected_at=datetime.now().isoformat(),
                    category_confidence=confidence
                )
                
                self.detector.save_important_message(msg)
                logger.debug(f"📊 Message important détecté: {subject[:30]}... (score: {score})")
        except Exception as e:
            logger.error(f"Erreur scoring message: {e}")

    def _check_and_send_summary(self, mailbox: ProtonMailBox) -> None:
        """
        Vérifie si c'est l'heure d'envoyer un résumé et l'envoie si nécessaire.
        Called during main loop.
        """
        if not self.detector or not self.reporter:
            return
        
        try:
            current_hour = datetime.now().hour
            
            # Vérifier si l'heure actuelle est dans la liste des heures de rapport
            if current_hour in SUMMARY_HOURS and current_hour != self.last_summary_hour:
                logger.info(f"🔔 Heure du rapport Executive Summary ({current_hour}:00 CET)")
                
                # Charger les messages importants
                messages = self.detector._load_important_messages()
                
                if messages:
                    # Générer le résumé
                    summary = self.detector.generate_executive_summary(messages)
                    
                    # Générer et envoyer le rapport HTML
                    html_content = self.reporter.generate_html_report(summary)
                    
                    if SUMMARY_FORMAT in ["email", "both"]:
                        success = self.reporter.send_summary_email(html_content)
                        if success:
                            logger.success(f"📧 Résumé envoyé à {self.reporter.summary_folder}")
                    
                    if SUMMARY_FORMAT in ["console", "both"]:
                        logger.info(f"📋 Résumé: {summary['urgent_count']} urgent, {summary['high_count']} high, {summary['medium_count']} medium")
                    
                    # Sauvegarder les backups locaux
                    self.reporter.save_summary_locally(summary, html_content)
                    
                    # Marquer l'heure pour éviter les doublons
                    self.last_summary_hour = current_hour
                else:
                    logger.debug(f"Aucun message important à rapporter à {current_hour}:00")
                    self.last_summary_hour = current_hour
        
        except Exception as e:
            logger.error(f"Erreur lors de la génération du résumé: {e}")

    def process_folder(self, mailbox: ProtonMailBox, folder_name: str = "INBOX") -> int:
        """
        Traite les emails d'un dossier spécifique.
        Récupère, parse, classifie et déplace les emails.
        + Scoring pour Executive Summary.
        """
        processed_count = 0
        try:
            # Sélection du dossier avec échappement des guillemets
            try:
                mailbox.client.select(f'"{folder_name}"')
            except Exception as e:
                logger.error(f"Impossible de sélectionner le dossier {folder_name}: {e}")
                return 0

            # Critère de recherche basé sur le checkpoint
            if not self.initial_scan_done:
                criteria = 'ALL'
                logger.info("Premier démarrage : Scan de TOUS les emails.")
            elif self.last_check.get(folder_name):
                # Si on a déjà traité ce dossier, chercher seulement les nouveaux
                criteria = 'UNSEEN' if UNSEEN_ONLY else 'ALL'
                logger.debug(f"Recherche des nouveaux emails ({criteria}) dans {folder_name}...")
            else:
                # Premier passage dans ce dossier depuis le checkpoint
                criteria = 'UNSEEN' if UNSEEN_ONLY else 'ALL'
                logger.info(f"Premier scan de {folder_name}, recherche: {criteria}")
            
            status, messages = mailbox.client.search(None, criteria)
            if status != 'OK' or not messages[0]:
                logger.debug(f"Aucun email à traiter dans {folder_name}.")
                # ✅ FIX: Ne PAS marquer les dossiers vides comme traités pendant le scan initial
                # Cela permet de les rescanner lors du prochain cycle si de nouveaux emails arrivent
                if self.initial_scan_done:
                    # Après le scan initial, on peut marquer les dossiers vides
                    self.last_check[folder_name] = datetime.now().isoformat()
                return 0

            email_ids = messages[0].split()
            total_emails = len(email_ids)
            
            # Déterminer la limite selon le type de dossier
            folder_lower = folder_name.lower()
            if 'spam' in folder_lower or 'trash' in folder_lower or 'corbeille' in folder_lower:
                limit = SPAM_TRASH_LIMIT
                logger.info(f"🗑️  Dossier Spam/Trash détecté, limitation à {limit} emails les plus récents")
            else:
                limit = MAX_EMAILS_PER_FOLDER
            
            # Trier et limiter les emails par date
            if total_emails > limit:
                logger.warning(f"⚠️  {total_emails} emails trouvés dans {folder_name}, tri par date pour garder les {limit} plus récents")
                email_ids = self._sort_emails_by_date(mailbox, email_ids, limit)
            
            logger.info(f"{len(email_ids)} email(s) trouvé(s) dans {folder_name} (sur {total_emails} total)")

            for email_id in email_ids:
                if not self.running:
                    break

                email_uid = email_id.decode()
                
                # ⚠️ Éviter de retraiter les emails déjà traités
                email_key = f"{folder_name}:{email_uid}"
                if email_key in self.processed_emails:
                    logger.debug(f"Email {email_uid} déjà traité, skip")
                    continue

                try:
                    # Récupérer le flag SEEN AVANT traitement
                    res_flags, flags_data = mailbox.client.fetch(email_id, '(FLAGS)')
                    was_seen = b'\\Seen' in flags_data[0] if res_flags == 'OK' and flags_data[0] else False
                    
                    res, msg_data = mailbox.client.fetch(email_id, '(RFC822)')
                    if res != 'OK':
                        logger.error(f"Erreur fetch email ID {email_uid}")
                        continue

                    raw_email = msg_data[0][1]
                    
                    # Parsing
                    subject, sender, body = self.parser.parse(raw_email)
                    
                    # Classification
                    result = self.classifier.classify(email_uid, subject, body)
                    category = result.category
                    confidence = result.confidence

                    logger.info(f"Email '{subject[:30]}...' -> {category} ({confidence:.2f})")

                    # 🆕 SCORING POUR EXECUTIVE SUMMARY
                    if SUMMARY_ENABLED:
                        self._score_and_track_message(email_uid, sender, subject, body, category, confidence)

                    # Déplacement
                    target_folder = self._get_target_folder(category)
                    
                    if target_folder:
                        if not DRY_RUN:
                            # S'assurer que le dossier de destination existe
                            if not self.ensure_folder_exists(mailbox, target_folder):
                                logger.error(f"Impossible de créer le dossier {target_folder}, email non déplacé")
                                continue

                            # Tentative de copie avec logs détaillés
                            logger.debug(f"Tentative COPY email {email_uid} vers '{target_folder}'")
                            try:
                                res, data = mailbox.client.copy(email_id, f'"{target_folder}"')
                                logger.debug(f"Réponse COPY: status={res}, data={data}")
                                
                                if res == 'OK':
                                    # Marquer pour suppression
                                    mailbox.client.store(email_id, '+FLAGS', '\\Deleted')
                                    
                                    # ✅ IMPORTANT : Restaurer le flag SEEN si l'email était déjà lu
                                    if was_seen:
                                        logger.debug(f"Email était déjà lu, flag SEEN préservé")
                                    
                                    logger.success(f"✓ Déplacé vers {target_folder}")
                                    processed_count += 1
                                    
                                    # Marquer comme traité
                                    self.processed_emails.add(email_key)
                                else:
                                    logger.error(f"Échec copie vers {target_folder}: {res} - {data}")
                            except Exception as copy_error:
                                logger.error(f"Exception lors de COPY vers {target_folder}: {copy_error}")
                        else:
                            logger.info(f"[DRY-RUN] Serait déplacé vers {target_folder}")
                            self.processed_emails.add(email_key)  # Même en dry-run pour tests
                    else:
                        logger.debug("Pas de déplacement (Catégorie UNKNOWN ou pas de dossier cible)")
                        self.processed_emails.add(email_key)  # Marquer quand même pour ne pas re-classifier

                except Exception as e:
                    logger.error(f"Erreur traitement email {email_uid}: {e}")
                    continue

            # Purge
            if not DRY_RUN and processed_count > 0:
                logger.info(f"Purge de {processed_count} email(s) déplacé(s) de {folder_name}...")
                mailbox.client.expunge()
                logger.success(f"✓ Purge terminée pour {folder_name}.")
            
            # ✅ Mettre à jour la date de dernière vérification SEULEMENT si des emails ont été traités
            # Ou si le scan initial est terminé
            self.last_check[folder_name] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Erreur critique traitement dossier {folder_name}: {e}")
        
        return processed_count

    def run(self):
        """Boucle principale du service avec Executive Summary scheduling."""
        logger.info("Démarrage de la boucle de traitement...")

        # ✅ Dossiers système à exclure (UNIQUEMENT les dossiers techniques IMAP)
        SYSTEM_FOLDERS = [
            "All Mail", "Tous les messages",
            "Labels/[Imap]",
            "Labels/[Imap]/Sent",
            "Labels/[Imap]/Trash",
            "Labels/[Imap]\\",
            "Labels/[Imap]\\/Trash",
            "Labels/[Imap]\\/Sent",
        ]

        while self.running:
            try:
                with self.connect_mailbox() as mailbox:
                    
                    # Initialiser le reporter avec la connexion IMAP (v1.1.0)
                    if SUMMARY_ENABLED and self.reporter is None:
                        self.reporter = SummaryEmailReporter(imap_connection=mailbox)
                    
                    # FeedbackManager
                    if not self.feedback_manager:
                        self.feedback_manager = FeedbackManager(self.classifier, mailbox)
                    else:
                        self.feedback_manager.mailbox = mailbox

                    self.feedback_manager.check_for_feedback()

                    # Traiter tous les dossiers
                    status, folders = mailbox.client.list()
                    total_processed = 0
                    folders_scanned = 0
                    
                    if status == 'OK':
                        for folder_bytes in folders:
                            try:
                                folder_raw = folder_bytes.decode('utf-8')
                            except UnicodeDecodeError:
                                folder_raw = folder_bytes.decode('latin-1')

                            # ✅ FIX: Parser correctement le format IMAP LIST
                            # Format: (\\Flags) "/" "Nom/Du/Dossier"
                            parts = folder_raw.split('"')
                            if len(parts) >= 3:
                                # Le nom est entre les deux derniers guillemets (avant-dernier élément)
                                folder_name = parts[-2]
                            else:
                                # Fallback si format inattendu
                                logger.warning(f"Format de dossier inattendu: {folder_raw}")
                                continue
                            
                            # ✅ Filtrer UNIQUEMENT les dossiers système IMAP et Training/Feedback
                            if (folder_name not in SYSTEM_FOLDERS and 
                                not folder_name.startswith("Training") and 
                                not folder_name.startswith("Feedback")):
                                
                                logger.debug(f"Scan du dossier: {folder_name}")
                                count = self.process_folder(mailbox, folder_name)
                                total_processed += count
                                folders_scanned += 1
                    
                    # 🆕 VÉRIFIER ET ENVOYER LE RÉSUMÉ (v1.1.0)
                    if SUMMARY_ENABLED:
                        self._check_and_send_summary(mailbox)
                    
                    # Sauvegarder le checkpoint après chaque cycle
                    self._save_checkpoint()
                    
                    if total_processed > 0:
                        logger.info(f"Cycle terminé. {total_processed} emails traités sur {folders_scanned} dossiers scannés.")
                    else:
                        logger.debug(f"Cycle terminé. Aucun email traité ({folders_scanned} dossiers scannés).")

                    if not self.initial_scan_done:
                        self.initial_scan_done = True
                        self._save_checkpoint()
                        logger.success("✓ Scan initial terminé. Le système se concentrera désormais sur les nouveaux emails.")

                time.sleep(POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Erreur dans la boucle principale: {e}")
                self._save_checkpoint()  # Sauvegarder même en cas d'erreur
                time.sleep(10)
        
        logger.info("Arrêt du processeur.")


if __name__ == "__main__":
    try:
        processor = EmailProcessor()
        processor.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.critical(f"Crash fatal: {e}")
        sys.exit(1)