#!/usr/bin/env python3
# ============================================================================
# EMAIL PROCESSOR - ProtonLumoAI
# Processeur principal avec gestion STARTTLS et Parsing Robuste
# ============================================================================

import os
import time
import signal
import sys
import ssl
import imaplib
from pathlib import Path
from typing import Optional

from loguru import logger
from dotenv import load_dotenv

# Import des modules locaux
# Assurez-vous que le PYTHONPATH est correct ou que les scripts sont dans le même dossier
try:
    from email_classifier import EmailClassifier
    from email_parser import EmailParser
    from feedback_manager import FeedbackManager
except ImportError:
    # Fallback pour exécution directe depuis le dossier scripts/
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from email_classifier import EmailClassifier
    from email_parser import EmailParser
    from feedback_manager import FeedbackManager

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
        self._connect()
    
    def _connect(self):
        """Établit la connexion STARTTLS avec ProtonMail Bridge"""
        try:
            # Contexte SSL permissif pour le certificat auto-signé du Bridge
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # 1. Connexion TCP simple (non chiffrée au départ)
            logger.debug(f"Connexion IMAP à {self.host}:{self.port}...")
            self.client = imaplib.IMAP4(self.host, self.port, timeout=self.timeout)
            
            # 2. Upgrade vers TLS via STARTTLS
            logger.debug("Envoi de la commande STARTTLS...")
            self.client.starttls(ssl_context=ssl_context)
            
            # 3. Authentification
            logger.debug(f"Authentification pour {self.username}...")
            self.client.login(self.username, self.password)
            
            logger.success(f"Connexion établie avec succès ({self.host}:{self.port})")
            
        except Exception as e:
            logger.error(f"Échec de la connexion IMAP/STARTTLS : {e}")
            if self.client:
                try:
                    self.client.logout()
                except:
                    pass
            raise

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Ferme proprement la connexion"""
        if self.client:
            try:
                self.client.close() # Close selected folder
            except:
                pass
            try:
                self.client.logout() # Logout from server
            except:
                pass


class EmailProcessor:
    """Processeur principal orchestrant le tri et l'apprentissage."""

    def __init__(self):
        self.classifier = EmailClassifier()
        self.parser = EmailParser()
        # FeedbackManager sera initialisé avec une connexion active
        self.feedback_manager: Optional[FeedbackManager] = None
        self.running = True
        self.initial_scan_done = False
        
        # Gestion des signaux pour arrêt propre (Ctrl+C)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info(f"EmailProcessor démarré [Dry Run: {DRY_RUN}, Unseen Only: {UNSEEN_ONLY}]")

    def _signal_handler(self, sig, frame):
        logger.info("Signal d'arrêt reçu. Fermeture...")
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

    def process_folder(self, mailbox: ProtonMailBox, folder_name: str = "INBOX") -> int:
        """
        Traite les emails d'un dossier spécifique.
        Récupère, parse, classifie et déplace les emails.
        """
        processed_count = 0
        try:
            # Sélection du dossier
            mailbox.client.select(f'"{folder_name}"')

            # Critère de recherche
            # Modification pour le scan initial
            if not self.initial_scan_done:
                criteria = 'ALL'
                logger.info("Premier démarrage : Scan de TOUS les emails.")
            else:
                criteria = 'UNSEEN' if UNSEEN_ONLY else 'ALL'
            logger.debug(f"Recherche d'emails ({criteria}) dans {folder_name}...")
            
            status, messages = mailbox.client.search(None, criteria)
            if status != 'OK' or not messages[0]:
                logger.debug("Aucun email à traiter.")
                return 0

            email_ids = messages[0].split()
            logger.info(f"{len(email_ids)} email(s) trouvé(s) dans {folder_name}")

            for email_id in email_ids:
                if not self.running:
                    break

                try:
                    # Récupération du contenu complet (RFC822)
                    res, msg_data = mailbox.client.fetch(email_id, '(RFC822)')
                    if res != 'OK':
                        logger.error(f"Erreur fetch email ID {email_id}")
                        continue

                    raw_email = msg_data[0][1]
                    
                    # 1. Parsing robuste
                    subject, sender, body = self.parser.parse(raw_email)
                    
                    # 2. Classification
                    result = self.classifier.classify(email_id.decode(), subject, body)
                    category = result.category
                    confidence = result.confidence

                    logger.info(f"Email '{subject[:30]}...' -> {category} ({confidence:.2f})")

                    # 3. Action (Déplacement)
                    target_folder = self._get_target_folder(category)
                    
                    if target_folder:
                        if not DRY_RUN:
                            # S'assurer que le dossier existe avant de copier
                            mailbox.client.create(f'"{target_folder}"')

                            res, _ = mailbox.client.copy(email_id, f'"{target_folder}"')
                            if res == 'OK':
                                # Marquer pour suppression dans la source (déplacement = copy + delete)
                                mailbox.client.store(email_id, '+FLAGS', '\\Deleted')
                                logger.success(f"✓ Déplacé vers {target_folder}")
                                processed_count += 1
                            else:
                                logger.error(f"Échec copie vers {target_folder}")
                        else:
                            logger.info(f"[DRY-RUN] Serait déplacé vers {target_folder}")
                    else:
                        logger.debug("Pas de déplacement (Catégorie UNKNOWN ou pas de dossier cible)")

                except Exception as e:
                    logger.error(f"Erreur traitement email {email_id.decode('utf-8', 'ignore')}: {e}")
                    continue

            # Appliquer les suppressions (expunge)
            if not DRY_RUN and processed_count > 0:
                mailbox.client.expunge()

        except Exception as e:
            logger.error(f"Erreur critique traitement dossier {folder_name}: {e}")
        
        return processed_count

    def run(self):
        """Boucle principale du service."""
        logger.info("Démarrage de la boucle de traitement...")

        # Liste des dossiers à NE PAS scanner (Dossiers systèmes et destination)
        # Adaptez cette liste selon les noms exacts dans votre ProtonMail
        EXCLUDED_FOLDERS = [
            "Trash", "Corbeille", 
            "Spam", "Junk",
            "Archive", 
            "Sent", "Sent Messages", "Envoyés",
            "Drafts", "Brouillons",
            "All Mail", "Tous les messages",
            "Folders/GMAIL" # Exclure le dossier d'archive volumineux
        ]

        while self.running:
            try:
                # Connexion (nouvelle à chaque cycle pour éviter les timeouts)
                with self.connect_mailbox() as mailbox:
                    
                    # 1. Initialiser le FeedbackManager
                    if not self.feedback_manager:
                        self.feedback_manager = FeedbackManager(self.classifier, mailbox)
                    else:
                        self.feedback_manager.mailbox = mailbox

                    # 2. Vérifier les corrections (Feedback Loop)
                    self.feedback_manager.check_for_feedback()

                    # 3. Traiter TOUS les dossiers (Modification ici)
                    status, folders = mailbox.client.list()
                    total_processed = 0
                    
                    if status == 'OK':
                        for folder_bytes in folders:
                            # Décodage robuste du nom du dossier
                            # Format typique: (\HasNoChildren) "/" "NomDuDossier"
                            try:
                                folder_raw = folder_bytes.decode('utf-8')
                            except UnicodeDecodeError:
                                folder_raw = folder_bytes.decode('latin-1') # Fallback

                            parts = folder_raw.split(' "/" ')
                            if len(parts) > 1:
                                folder_name = parts[-1].strip('"')
                            else:
                                continue # Skip invalid folder format
                            
                            # Ignorer les dossiers exclus et les dossiers d'entraînement/feedback
                            if (folder_name not in EXCLUDED_FOLDERS and 
                                not folder_name.startswith("Training") and 
                                not folder_name.startswith("Feedback")):
                                
                                logger.debug(f"Scan du dossier: {folder_name}")
                                count = self.process_folder(mailbox, folder_name)
                                total_processed += count
                    
                    if total_processed > 0:
                        logger.info(f"Cycle terminé. {total_processed} emails traités au total.")
                    else:
                        logger.debug("Cycle terminé. Aucun changement.")

                    # Marquer le scan initial comme terminé
                    if not self.initial_scan_done:
                        self.initial_scan_done = True
                        logger.success("Scan initial terminé. Le système se concentrera désormais sur les nouveaux emails.")

                # Attente avant le prochain cycle
                time.sleep(POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Erreur dans la boucle principale: {e}")
                time.sleep(10)
        
        logger.info("Arrêt du processeur.")


if __name__ == "__main__":
    # Point d'entrée
    try:
        processor = EmailProcessor()
        processor.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.critical(f"Crash fatal: {e}")
        sys.exit(1)
