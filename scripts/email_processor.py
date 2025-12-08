#!/usr/bin/env python3
# ============================================================================
# EMAIL PROCESSOR - ProtonLumoAI
# Processeur principal avec gestion STARTTLS et Parsing Robuste
# + Executive Summary v1.1.0
# + Performance Optimization v1.2.0 (Parallel & Batch)
# ============================================================================

import os
import time
import signal
import sys
import ssl
import imaplib
import json
import re
from pathlib import Path
from typing import Optional, Set, Dict, List, Tuple
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
    from email_classifier_batch import BatchClassifier, BatchEmail
    from email_processor_parallel import ParallelProcessor, ProcessingMetrics
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from email_classifier import EmailClassifier
    from email_parser import EmailParser
    from feedback_manager import FeedbackManager
    from important_message_detector import ImportantMessageDetector, ImportantMessage
    from summary_email_reporter import SummaryEmailReporter
    from email_classifier_batch import BatchClassifier, BatchEmail
    from email_processor_parallel import ParallelProcessor, ProcessingMetrics

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
        """Établit la connexion STARTTLS avec ProtonMail Bridge"""
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
                    
                    parts = folder_raw.split('"')
                    if len(parts) >= 3:
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
            
        # === PERFORMANCE SETTINGS (v1.2.0) ===
        self.enable_parallel = os.getenv("PROTON_LUMO_ENABLE_PARALLEL", "true").lower() == "true"
        self.max_workers = int(os.getenv("PROTON_LUMO_MAX_WORKERS", 5))
        self.enable_batch = os.getenv("PROTON_LUMO_ENABLE_BATCH", "true").lower() == "true"
        self.batch_size = int(os.getenv("PROTON_LUMO_BATCH_SIZE", 10))
        self.metrics_enabled = os.getenv("PROTON_LUMO_METRICS_ENABLED", "true").lower() == "true"

        # Initialize optimizers
        if self.enable_parallel:
            self.parallel_processor = ParallelProcessor(
                max_workers=self.max_workers,
                enable_metrics=self.metrics_enabled
            )
        else:
            self.parallel_processor = None

        if self.enable_batch:
            self.batch_classifier = BatchClassifier(
                enable_batch=True,
                batch_size=self.batch_size
            )
        else:
            self.batch_classifier = None

        logger.info(
            f"Performance settings: parallel={self.enable_parallel} "
            f"({self.max_workers} workers), batch={self.enable_batch} (size={self.batch_size})"
        )
        
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
        if mailbox.folder_exists(folder_path):
            return True
        
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
                    time.sleep(0.5)
                    mailbox._refresh_folder_cache()
                    if mailbox.folder_exists(current_path):
                        logger.success(f"✓ Dossier créé: {current_path}")
                    else:
                        mailbox._existing_folders.add(current_path)
                except Exception as e:
                    logger.error(f"Impossible de créer le dossier {current_path}: {e}")
                    return False
        return True

    def _get_email_date(self, mailbox: ProtonMailBox, email_id: bytes) -> datetime:
        """Récupère la date d'un email pour le tri."""
        try:
            res_flags, flags_data = mailbox.client.fetch(email_id, '(INTERNALDATE)')
            if res_flags == 'OK' and flags_data and flags_data[0]:
                date_str = flags_data[0].decode('utf-8', errors='ignore')
                match = re.search(r'"([^"]+)"', date_str)
                if match:
                    date_tuple = email.utils.parsedate_tz(match.group(1))
                    if date_tuple:
                        return datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
        except Exception as e:
            logger.debug(f"Erreur récupération date email: {e}")
        return datetime.min

    def _sort_emails_by_date(self, mailbox: ProtonMailBox, email_ids: List[bytes], limit: int) -> List[bytes]:
        """Trie les emails par date décroissante et retourne les {limit} plus récents."""
        if not email_ids or len(email_ids) <= limit:
            return email_ids
        
        logger.debug(f"Tri de {len(email_ids)} emails par date pour garder les {limit} plus récents...")
        emails_with_dates = []
        for email_id in email_ids:
            date = self._get_email_date(mailbox, email_id)
            emails_with_dates.append((email_id, date))
        
        emails_with_dates.sort(key=lambda x: x[1], reverse=True)
        recent_emails = [email_id for email_id, _ in emails_with_dates[:limit]]
        logger.debug(f"✓ {len(recent_emails)} emails les plus récents sélectionnés")
        return recent_emails

    def _score_and_track_message(self, email_uid: str, from_email: str, subject: str, body: str, category: str, confidence: float) -> None:
        """Score le message pour l'Executive Summary et le sauvegarde."""
        if not self.detector:
            return
        try:
            score, breakdown, action_type = self.detector.score_message(
                email_uid, from_email, subject, body, category, confidence
            )
            if score >= SUMMARY_MIN_SCORE:
                msg = ImportantMessage(
                    message_id=email_uid,
                    from_email=from_email,
                    subject=subject[:100],
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
        """Vérifie si c'est l'heure d'envoyer un résumé et l'envoie si nécessaire."""
        if not self.detector or not self.reporter:
            return
        try:
            current_hour = datetime.now().hour
            if current_hour in SUMMARY_HOURS and current_hour != self.last_summary_hour:
                logger.info(f"🔔 Heure du rapport Executive Summary ({current_hour}:00 CET)")
                messages = self.detector._load_important_messages()
                if messages:
                    summary = self.detector.generate_executive_summary(messages)
                    html_content = self.reporter.generate_html_report(summary)
                    if SUMMARY_FORMAT in ["email", "both"]:
                        success = self.reporter.send_summary_email(html_content)
                        if success:
                            logger.success(f"📧 Résumé envoyé à {self.reporter.summary_folder}")
                    if SUMMARY_FORMAT in ["console", "both"]:
                        logger.info(f"📋 Résumé: {summary['urgent_count']} urgent, {summary['high_count']} high")
                    self.reporter.save_summary_locally(summary, html_content)
                    self.last_summary_hour = current_hour
                else:
                    logger.debug(f"Aucun message important à rapporter à {current_hour}:00")
                    self.last_summary_hour = current_hour
        except Exception as e:
            logger.error(f"Erreur lors de la génération du résumé: {e}")

    def _classify_batch(self, email_ids: List[bytes], mailbox) -> Dict[str, Tuple[str, float]]:
        """
        Classify multiple emails in batches (v1.2.0 optimization)
        
        Args:
            email_ids: List of email IDs from IMAP
            mailbox: IMAP connection object
            
        Returns:
            Dict mapping email_id → (category, confidence)
        """
        if not self.enable_batch or not self.batch_classifier:
            return {}
        
        logger.info(f"Using batch classification (size={self.batch_size}) for {len(email_ids)} emails")
        
        batch_emails = []
        for email_id in email_ids:
            try:
                res, msg_data = mailbox.client.fetch(email_id, '(RFC822)')
                if res == 'OK':
                    raw_email = msg_data[0][1]
                    subject, sender, body = self.parser.parse(raw_email)
                    body_truncated = body[:500]
                    
                    batch_emails.append(
                        BatchEmail(
                            email_id=email_id.decode(),
                            subject=subject,
                            body=body_truncated
                        )
                    )
            except Exception as e:
                logger.error(f"Error fetching email {email_id}: {e}")
                continue
        
        if not batch_emails:
            return {}
        
        valid_categories = list(self.classifier.categories.keys())
        results = {}
        
        for i in range(0, len(batch_emails), self.batch_size):
            batch_chunk = batch_emails[i:i + self.batch_size]
            classifications = self.batch_classifier.classify_batch(batch_chunk, valid_categories)
            results.update(classifications)
        
        formatted_results = {}
        for eid, data in results.items():
            formatted_results[eid] = (data['category'], data['confidence'])
            
        logger.info(f"Batch classification complete: {len(formatted_results)} emails classified")
        return formatted_results

    def process_folder(self, mailbox: ProtonMailBox, folder_name: str = "INBOX") -> int:
        """
        Traite les emails d'un dossier spécifique.
        Récupère, parse, classifie et déplace les emails.
        + Scoring pour Executive Summary.
        + Support Parallel & Batch Processing (v1.2.0)
        """
        processed_count = 0
        try:
            try:
                mailbox.client.select(f'"{folder_name}"')
            except Exception as e:
                logger.error(f"Impossible de sélectionner le dossier {folder_name}: {e}")
                return 0

            if not self.initial_scan_done:
                criteria = 'ALL'
                logger.info("Premier démarrage : Scan de TOUS les emails.")
            elif self.last_check.get(folder_name):
                criteria = 'UNSEEN' if UNSEEN_ONLY else 'ALL'
                logger.debug(f"Recherche des nouveaux emails ({criteria}) dans {folder_name}...")
            else:
                criteria = 'UNSEEN' if UNSEEN_ONLY else 'ALL'
                logger.info(f"Premier scan de {folder_name}, recherche: {criteria}")
            
            status, messages = mailbox.client.search(None, criteria)
            if status != 'OK' or not messages[0]:
                logger.debug(f"Aucun email à traiter dans {folder_name}.")
                if self.initial_scan_done:
                    self.last_check[folder_name] = datetime.now().isoformat()
                return 0

            email_ids = messages[0].split()
            total_emails = len(email_ids)
            
            folder_lower = folder_name.lower()
            if 'spam' in folder_lower or 'trash' in folder_lower or 'corbeille' in folder_lower:
                limit = SPAM_TRASH_LIMIT
                logger.info(f"🗑️  Dossier Spam/Trash détecté, limitation à {limit} emails les plus récents")
            else:
                limit = MAX_EMAILS_PER_FOLDER
            
            if total_emails > limit:
                logger.warning(f"⚠️  {total_emails} emails trouvés dans {folder_name}, tri par date pour garder les {limit} plus récents")
                email_ids = self._sort_emails_by_date(mailbox, email_ids, limit)
            
            logger.info(f"{len(email_ids)} email(s) trouvé(s) dans {folder_name} (sur {total_emails} total)")

            batch_classifications = {}
            if self.enable_batch and len(email_ids) > 1:
                emails_to_classify = []
                for eid in email_ids:
                    uid = eid.decode()
                    key = f"{folder_name}:{uid}"
                    if key not in self.processed_emails:
                        emails_to_classify.append(eid)
                
                if emails_to_classify:
                    batch_classifications = self._classify_batch(emails_to_classify, mailbox)

            for email_id in email_ids:
                if not self.running:
                    break
                    
                email_uid = email_id.decode()
                email_key = f"{folder_name}:{email_uid}"
                
                if email_key in self.processed_emails:
                    continue

                try:
                    res_flags, flags_data = mailbox.client.fetch(email_id, '(FLAGS)')
                    was_seen = b'\\Seen' in flags_data[0] if res_flags == 'OK' and flags_data[0] else False
                    
                    if email_uid in batch_classifications:
                        category, confidence = batch_classifications[email_uid]
                        
                        res, msg_data = mailbox.client.fetch(email_id, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])')
                        if res == 'OK':
                            raw_header = msg_data[0][1]
                            msg = email.message_from_bytes(raw_header)
                            try:
                                subject_header = msg['Subject']
                                if subject_header:
                                    decoded_parts = email.header.decode_header(subject_header)
                                    subject = decoded_parts[0][0]
                                    if isinstance(subject, bytes):
                                        subject = subject.decode()
                                else:
                                    subject = "Unknown"
                            except:
                                subject = "Unknown"
                            sender = msg['From'] or "Unknown"
                            body = "Batch processed body"
                        else:
                            subject = "Unknown"
                            sender = "Unknown"
                            body = ""
                            
                        logger.info(f"⚡ Batch Result: '{subject[:30]}...' -> {category} ({confidence:.2f})")
                        
                    else:
                        res, msg_data = mailbox.client.fetch(email_id, '(RFC822)')
                        if res != 'OK':
                            continue
                        raw_email = msg_data[0][1]
                        subject, sender, body = self.parser.parse(raw_email)
                        result = self.classifier.classify(email_uid, subject, body)
                        category = result.category
                        confidence = result.confidence
                        logger.info(f"Email '{subject[:30]}...' -> {category} ({confidence:.2f})")

                    if SUMMARY_ENABLED:
                        self._score_and_track_message(email_uid, sender, subject, body, category, confidence)

                    target_folder = self._get_target_folder(category)
                    if target_folder:
                        if not DRY_RUN:
                            if not self.ensure_folder_exists(mailbox, target_folder):
                                continue
                            res, data = mailbox.client.copy(email_id, f'"{target_folder}"')
                            if res == 'OK':
                                mailbox.client.store(email_id, '+FLAGS', '\\Deleted')
                                if was_seen:
                                    logger.debug("Preserving SEEN flag")
                                logger.success(f"✓ Moved to {target_folder}")
                                processed_count += 1
                                self.processed_emails.add(email_key)
                            else:
                                logger.error(f"Copy failed: {res} - {data}")
                        else:
                            logger.info(f"[DRY-RUN] Would move to {target_folder}")
                            self.processed_emails.add(email_key)
                    else:
                        self.processed_emails.add(email_key)

                except Exception as e:
                    logger.error(f"Error processing email {email_uid}: {e}")
                    continue

            if not DRY_RUN and processed_count > 0:
                logger.info(f"Purging {processed_count} emails from {folder_name}...")
                mailbox.client.expunge()
            
            self.last_check[folder_name] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Critical error in folder {folder_name}: {e}")
        
        return processed_count

    def run(self):
        """Boucle principale du service."""
        logger.info("Démarrage de la boucle de traitement...")
        SYSTEM_FOLDERS = [
            "All Mail", "Tous les messages",
            "Labels/[Imap]", "Labels/[Imap]/Sent", "Labels/[Imap]/Trash",
            "Labels/[Imap]\\", "Labels/[Imap]\\/Trash", "Labels/[Imap]\\/Sent",
        ]

        while self.running:
            try:
                with self.connect_mailbox() as mailbox:
                    if SUMMARY_ENABLED and self.reporter is None:
                        self.reporter = SummaryEmailReporter(imap_connection=mailbox)
                    if not self.feedback_manager:
                        self.feedback_manager = FeedbackManager(self.classifier, mailbox)
                    else:
                        self.feedback_manager.mailbox = mailbox
                    self.feedback_manager.check_for_feedback()

                    status, folders = mailbox.client.list()
                    total_processed = 0
                    folders_scanned = 0
                    
                    if status == 'OK':
                        for folder_bytes in folders:
                            try:
                                folder_raw = folder_bytes.decode('utf-8')
                            except UnicodeDecodeError:
                                folder_raw = folder_bytes.decode('latin-1')
                            parts = folder_raw.split('"')
                            if len(parts) >= 3:
                                folder_name = parts[-2]
                            else:
                                continue
                            
                            if (folder_name not in SYSTEM_FOLDERS and 
                                not folder_name.startswith("Training") and 
                                not folder_name.startswith("Feedback")):
                                count = self.process_folder(mailbox, folder_name)
                                total_processed += count
                                folders_scanned += 1
                    
                    if SUMMARY_ENABLED:
                        self._check_and_send_summary(mailbox)
                    
                    self._save_checkpoint()
                    if total_processed > 0:
                        logger.info(f"Cycle terminé. {total_processed} emails traités.")
                    
                    if not self.initial_scan_done:
                        self.initial_scan_done = True
                        self._save_checkpoint()
                        logger.success("✓ Scan initial terminé.")

                time.sleep(POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Erreur dans la boucle principale: {e}")
                self._save_checkpoint()
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
