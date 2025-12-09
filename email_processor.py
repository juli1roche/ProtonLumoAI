#!/usr/bin/env python3

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
from concurrent.futures import ThreadPoolExecutor, ascompleted

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

from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Configuration IMAP
PROTON_BRIDGE_HOST = os.getenv('PROTON_BRIDGE_HOST', '127.0.0.1')
PROTON_BRIDGE_PORT = int(os.getenv('PROTON_BRIDGE_PORT', 1143))
PROTON_USERNAME = os.getenv('PROTON_USERNAME')
PROTON_PASSWORD = os.getenv('PROTON_PASSWORD')
POLL_INTERVAL = int(os.getenv('PROTONLUMO_POLL_INTERVAL', 60))
UNSEEN_ONLY = os.getenv('PROTONLUMO_UNSEEN_ONLY', 'true').lower() == 'true'
DRY_RUN = os.getenv('PROTONLUMO_DRY_RUN', 'false').lower() == 'true'
MAX_EMAILS_PER_FOLDER = int(os.getenv('PROTONLUMO_MAX_EMAILS_PER_FOLDER', 100))

# Configuration Executive Summary
SUMMARY_ENABLED = os.getenv('PROTONLUMO_SUMMARY_ENABLED', 'true').lower() == 'true'
SUMMARY_HOURS = list(map(int, os.getenv('PROTONLUMO_SUMMARY_HOURS', '09,13,17').split(',')))
SUMMARY_MIN_SCORE = int(os.getenv('PROTONLUMO_SUMMARY_MIN_SCORE', 30))
SUMMARY_FORMAT = os.getenv('PROTONLUMO_SUMMARY_FORMAT', 'email').lower()

# Limites spéciales
SPAM_TRASH_LIMIT = 10

DATA_DIR = Path(os.getenv('PROTONLUMO_DATA', '~/ProtonLumoAI/data')).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_FILE = DATA_DIR / 'checkpoint.json'


class ProtonMailBox:
    """Wrapper IMAP pour ProtonMail Bridge avec STARTTLS."""

    def __init__(self, host, port, username, password, timeout=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout or 10
        self.client: Optional[imaplib.IMAP4] = None
        self.existing_folders: Set[str] = set()
        self.connect()

    def connect(self):
        """Établit la connexion STARTTLS avec ProtonMail Bridge."""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            logger.debug(f'Connexion IMAP {self.host}:{self.port}...')
            self.client = imaplib.IMAP4(self.host, self.port, timeout=self.timeout)
            logger.debug('Envoi de la commande STARTTLS...')
            self.client.starttls(ssl_context)
            logger.debug(f'Authentification pour {self.username}...')
            self.client.login(self.username, self.password)
            logger.success(f'✓ Connexion établie avec succès {self.host}:{self.port}')
            self.refresh_folder_cache()
        except Exception as e:
            logger.error(f'Échec de la connexion IMAP/STARTTLS: {e}')
            if self.client:
                try:
                    self.client.logout()
                except:
                    pass
            raise

    def refresh_folder_cache(self):
        """Met à jour le cache des dossiers existants."""
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
                        self.existing_folders.add(folder_name)
        except Exception as e:
            logger.warning(f'Erreur lors de la mise à jour du cache des dossiers: {e}')

    def folder_exists(self, folder_path: str) -> bool:
        """Vérifie si un dossier existe."""
        return folder_path in self.existing_folders

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Ferme proprement la connexion."""
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
    """Processeur principal orchestrant le tri et l'apprentissage."""

    def __init__(self):
        self.classifier = EmailClassifier()
        self.parser = EmailParser()
        self.feedback_manager: Optional[FeedbackManager] = None
        self.running = True

        if SUMMARY_ENABLED:
            self.detector = ImportantMessageDetector()
            self.reporter = None
            self.last_summary_hour = -1
            logger.info(f'Executive Summary ACTIVÉ - Rapports {SUMMARY_HOURS} CET')
        else:
            self.detector = None
            self.reporter = None

        self.checkpoint = self.load_checkpoint()
        self.initial_scan_done = self.checkpoint.get('initial_scan_done', False)
        self.last_check: Dict[str, str] = self.checkpoint.get('last_check', {})
        self.processed_emails: Set[str] = set(self.checkpoint.get('processed_emails', []))

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        logger.info(f'EmailProcessor démarré (Dry Run: {DRY_RUN}, Unseen Only: {UNSEEN_ONLY}, Max/Folder: {MAX_EMAILS_PER_FOLDER})')
        if self.initial_scan_done:
            logger.info(f'Reprise depuis checkpoint ({len(self.processed_emails)} emails déjà traités)')

    def load_checkpoint(self) -> dict:
        """Charge le checkpoint depuis le disque."""
        if CHECKPOINT_FILE.exists():
            try:
                with open(CHECKPOINT_FILE, 'r') as f:
                    data = json.load(f)
                    logger.info(f'Checkpoint chargé: {CHECKPOINT_FILE}')
                    return data
            except Exception as e:
                logger.warning(f'Impossible de charger le checkpoint: {e}')
        return {}

    def save_checkpoint(self):
        """Sauvegarde le checkpoint sur disque."""
        try:
            checkpoint_data = {
                'initial_scan_done': self.initial_scan_done,
                'last_check': self.last_check,
                'processed_emails': list(self.processed_emails),
                'last_update': datetime.now().isoformat()
            }
            with open(CHECKPOINT_FILE, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            logger.debug(f'Checkpoint sauvegardé ({len(self.processed_emails)} emails traités)')
        except Exception as e:
            logger.error(f'Erreur sauvegarde checkpoint: {e}')

    def signal_handler(self, sig, frame):
        logger.info('Signal d\'arrêt reçu. Sauvegarde du checkpoint...')
        self.save_checkpoint()
        logger.info('Fermeture...')
        self.running = False

    def connect_mailbox(self) -> ProtonMailBox:
        """Crée et retourne une instance connectée de ProtonMailBox."""
        if not PROTON_USERNAME or not PROTON_PASSWORD:
            logger.error('Identifiants manquants. Vérifiez votre fichier .env')
            sys.exit(1)
        return ProtonMailBox(PROTON_BRIDGE_HOST, PROTON_BRIDGE_PORT, PROTON_USERNAME, PROTON_PASSWORD)

    def get_target_folder(self, category: str) -> Optional[str]:
        """Récupère le dossier cible pour une catégorie donnée."""
        if category == 'UNKNOWN':
            return None
        cat_obj = self.classifier.categories.get(category)
        if cat_obj:
            return cat_obj.folder
        return None

    def ensure_folder_exists(self, mailbox: ProtonMailBox, folder_path: str) -> bool:
        """S'assure qu'un dossier existe, le crée récursivement si nécessaire.
        
        Retourne True si le dossier existe ou a été créé, False en cas d'échec.
        """
        if mailbox.folder_exists(folder_path):
            logger.debug(f'Dossier {folder_path} déjà dans le cache')
            return True

        path_parts = folder_path.split('/')
        current_path = ''
        for part in path_parts:
            if current_path:
                current_path = current_path + '/' + part
            else:
                current_path = part

            if not mailbox.folder_exists(current_path):
                try:
                    logger.debug(f'Création du dossier {current_path}')
                    mailbox.client.create(f'"{current_path}"')
                    time.sleep(0.5)
                    mailbox.refresh_folder_cache()
                    if mailbox.folder_exists(current_path):
                        logger.success(f'Dossier créé: {current_path}')
                    else:
                        logger.warning(f'Dossier {current_path} créé mais absent du cache')
                        mailbox.existing_folders.add(current_path)
                except Exception as e:
                    logger.error(f'Impossible de créer le dossier {current_path}: {e}')
                    return False
        return True

    def get_email_date(self, mailbox: ProtonMailBox, email_id: bytes) -> datetime:
        """Récupère la date d'un email pour le tri.
        
        Retourne la date ou datetime.min si erreur.
        """
        try:
            res_flags, flags_data = mailbox.client.fetch(email_id, 'INTERNALDATE')
            if res_flags == 'OK' and flags_data and flags_data[0]:
                date_str = flags_data[0].decode('utf-8', errors='ignore')
                import re
                match = re.search(r'INTERNALDATE "([^"]+)"', date_str)
                if match:
                    date_tuple = email.utils.parsedate_tz(match.group(1))
                    if date_tuple:
                        return datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
        except Exception as e:
            logger.debug(f'Erreur récupération date email: {e}')
        return datetime.min

    def sort_emails_by_date(self, mailbox: ProtonMailBox, email_ids: List[bytes], limit: int) -> List[bytes]:
        """Trie les emails par date décroissante et retourne les limit plus récents."""
        if not email_ids or len(email_ids) <= limit:
            return email_ids

        logger.debug(f'Tri de {len(email_ids)} emails par date pour garder les {limit} plus récents...')
        emails_with_dates = []
        for email_id in email_ids:
            date = self.get_email_date(mailbox, email_id)
            emails_with_dates.append((email_id, date))

        emails_with_dates.sort(key=lambda x: x[1], reverse=True)
        recent_emails = [email_id for email_id, _ in emails_with_dates[:limit]]
        logger.debug(f'{len(recent_emails)} emails les plus récents sélectionnés')
        return recent_emails

    # ============================================================================
    # FIX v1.2.2: IMAP SEARCH BUG - CRITICAL FIX
    # ============================================================================
    # Bug: "command SEARCH illegal in state AUTH, only allowed in states SELECTED"
    # Root Cause: Client must SELECT a mailbox before executing SEARCH
    # Solution: Always SELECT the folder BEFORE executing any SEARCH command
    # ============================================================================

    def process_folder(self, mailbox: ProtonMailBox, folder_name: str = 'INBOX') -> int:
        """Traite les emails d'un dossier spécifique.
        
        Récupère, parse, classifie et déplace les emails.
        Scoring pour Executive Summary.
        """
        processed_count = 0
        try:
            # ========== FIX v1.2.2 ==========
            # CRITICAL: SELECT folder BEFORE executing any SEARCH/FETCH commands
            # This prevents "command SEARCH illegal in state AUTH" error
            # ===============================
            logger.debug(f'SELECT folder: {folder_name}')
            try:
                status, _ = mailbox.client.select(f'"{folder_name}"', readonly=False)
                if status != 'OK':
                    logger.error(f'Impossible de sélectionner le dossier {folder_name}: status={status}')
                    return 0
            except Exception as e:
                logger.error(f'Impossible de sélectionner le dossier {folder_name}: {e}')
                return 0

            # Now that folder is selected, we can execute SEARCH
            if not self.initial_scan_done:
                criteria = 'ALL'
                logger.info('Premier démarrage - Scan de TOUS les emails.')
            elif self.last_check.get(folder_name):
                criteria = 'UNSEEN' if UNSEEN_ONLY else 'ALL'
                logger.debug(f'Recherche des nouveaux emails ({criteria}) dans {folder_name}...')
            else:
                criteria = 'UNSEEN' if UNSEEN_ONLY else 'ALL'
                logger.info(f'Premier scan de {folder_name}, recherche {criteria}')

            # ========== SEARCH with proper STATE ==========
            status, messages = mailbox.client.search(None, criteria)
            if status != 'OK' or not messages[0]:
                logger.debug(f'Aucun email à traiter dans {folder_name}.')
                if self.initial_scan_done:
                    pass
                return 0

            email_ids = messages[0].split()
            total_emails = len(email_ids)

            # Limiter selon le type de dossier
            folder_lower = folder_name.lower()
            if any(x in folder_lower for x in ['spam', 'trash', 'corbeille']):
                limit = SPAM_TRASH_LIMIT
                logger.info(f'Dossier Spam/Trash détecté, limitation {limit} emails les plus récents')
            else:
                limit = MAX_EMAILS_PER_FOLDER

            if total_emails > limit:
                logger.warning(f'{total_emails} emails trouvés dans {folder_name}, tri par date pour garder les {limit} plus récents')
                email_ids = self.sort_emails_by_date(mailbox, email_ids, limit)

            logger.info(f'{len(email_ids)} emails trouvés dans {folder_name} sur {total_emails} total')

            for email_id in email_ids:
                if not self.running:
                    break

                email_uid = email_id.decode()
                email_key = f'{folder_name}:{email_uid}'

                if email_key in self.processed_emails:
                    logger.debug(f'Email {email_uid} déjà traité, skip')
                    continue

                try:
                    # ========== FETCH with proper STATE ==========
                    res_flags, flags_data = mailbox.client.fetch(email_id, 'FLAGS')
                    was_seen = b'\\Seen' in flags_data[0] if res_flags == 'OK' and flags_data[0] else False

                    res, msg_data = mailbox.client.fetch(email_id, 'RFC822')
                    if res != 'OK':
                        logger.error(f'Erreur fetch email ID {email_uid}')
                        continue

                    raw_email = msg_data[0][1]
                    email_obj = self.parser.parse(raw_email)
                    from_email = email_obj.get('from', 'unknown')
                    subject = email_obj.get('subject', '[Sans objet]')
                    body = email_obj.get('body', '')

                    # Classification
                    result = self.classifier.classify(email_uid, subject, body)
                    category = result.category
                    confidence = result.confidence
                    logger.info(f'Email {subject[:30]}... - {category} ({confidence:.2f}%)')

                    # Scoring pour Executive Summary
                    if category != 'UNKNOWN':
                        self.score_and_track_message(email_uid, from_email, subject, body, category, confidence)

                    # Déplacement
                    target_folder = self.get_target_folder(category)
                    if not target_folder or category == 'UNKNOWN':
                        logger.debug('Pas de déplacement - Catégorie UNKNOWN ou pas de dossier cible')
                        self.processed_emails.add(email_key)
                        continue

                    if not self.ensure_folder_exists(mailbox, target_folder):
                        logger.error(f'Impossible de créer le dossier {target_folder}, email non déplacé')
                        continue

                    if not DRY_RUN:
                        try:
                            res, data = mailbox.client.copy(email_id, f'"{target_folder}"')
                            if res == 'OK':
                                logger.debug(f'Tentative COPY email {email_uid} vers {target_folder}')
                                mailbox.client.store(email_id, '+FLAGS', '\\Deleted')
                                logger.success(f'Déplacé vers {target_folder}')
                                processed_count += 1
                            else:
                                logger.error(f'Echec COPY vers {target_folder}: {res} - {data}')
                        except Exception as copy_error:
                            logger.error(f'Exception lors de COPY vers {target_folder}: {copy_error}')
                    else:
                        logger.info(f'DRY-RUN: Serait déplacé vers {target_folder}')

                    self.processed_emails.add(email_key)

                except Exception as e:
                    logger.error(f'Erreur traitement email {email_uid}: {e}')
                    continue

            # ========== EXPUNGE after FOLDER SELECTION ==========
            if not DRY_RUN and processed_count > 0:
                logger.info(f'Purge de {processed_count} emails déplacés de {folder_name}...')
                mailbox.client.expunge()
                logger.success(f'Purge terminée pour {folder_name}.')

            self.last_check[folder_name] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f'Erreur critique traitement dossier {folder_name}: {e}')

        return processed_count

    def run(self):
        """Boucle principale du service avec Executive Summary scheduling."""
        logger.info('Démarrage de la boucle de traitement...')

        while self.running:
            try:
                with self.connect_mailbox() as mailbox:
                    if SUMMARY_ENABLED and self.reporter is None:
                        self.reporter = SummaryEmailReporter(imap_connection=mailbox)
                        logger.info('Reporter Executive Summary initialisé')

                    # Récupérer tous les dossiers
                    status, folders = mailbox.client.list()
                    total_processed = 0
                    folders_scanned = 0

                    if status == 'OK':
                        for folder_bytes in folders:
                            try:
                                folder_raw = folder_bytes.decode('utf-8')
                            except UnicodeDecodeError:
                                folder_raw = folder_bytes.decode('latin-1')

                            # Parser le nom du dossier
                            parts = folder_raw.split('"')
                            if len(parts) < 3:
                                logger.warning(f'Format de dossier inattendu: {folder_raw}')
                                continue
                            folder_name = parts[-2]

                            # Filtrer les dossiers système
                            system_folders = ['All Mail', 'Tous les messages', '[Gmail]', '[Imap]', '[Sent]', '[Trash]', '[Draft]']
                            if any(x in folder_name for x in system_folders):
                                logger.debug(f'Skip dossier système: {folder_name}')
                                continue

                            if folder_name.startswith('Training') or folder_name.startswith('Feedback'):
                                logger.debug(f'Skip dossier Training/Feedback: {folder_name}')
                                continue

                            logger.debug(f'Scan du dossier {folder_name}')
                            count = self.process_folder(mailbox, folder_name)
                            total_processed += count
                            folders_scanned += 1

                    # Executive Summary
                    if SUMMARY_ENABLED and self.detector and self.reporter:
                        self.check_and_send_summary(mailbox)

                    self.save_checkpoint()

                    if total_processed > 0:
                        logger.info(f'Cycle terminé. {total_processed} emails traités sur {folders_scanned} dossiers scannés.')
                    else:
                        logger.debug(f'Cycle terminé. Aucun email traité sur {folders_scanned} dossiers scannés.')

                    if not self.initial_scan_done:
                        self.initial_scan_done = True
                        self.save_checkpoint()
                        logger.success('✓ Scan initial terminé. Le système se concentrera désormais sur les nouveaux emails.')

            except Exception as e:
                logger.error(f'Erreur dans la boucle principale: {e}')
                self.save_checkpoint()
                time.sleep(10)

            time.sleep(POLL_INTERVAL)

        logger.info('Arrêt du processeur.')

    def score_and_track_message(self, email_uid: str, from_email: str, subject: str, body: str, category: str, confidence: float) -> None:
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
                    criteria=breakdown,
                    action_type=action_type,
                    status='new',
                    detected_at=datetime.now().isoformat(),
                    category_confidence=confidence
                )
                self.detector.save_important_message(msg)
                logger.debug(f'Message important détecté - {subject[:30]}... score {score}')
        except Exception as e:
            logger.error(f'Erreur scoring message: {e}')

    def check_and_send_summary(self, mailbox: ProtonMailBox) -> None:
        """Vérifie si c'est l'heure d'envoyer un résumé et l'envoie si nécessaire."""
        if not self.detector or not self.reporter:
            return
        try:
            current_hour = datetime.now().hour
            if current_hour in SUMMARY_HOURS and current_hour != self.last_summary_hour:
                logger.info(f'Heure du rapport Executive Summary: {current_hour}:00 CET')
                messages = self.detector.load_important_messages()
                if messages:
                    summary = self.detector.generate_executive_summary(messages)
                    html_content = self.reporter.generate_html_report(summary)
                    if SUMMARY_FORMAT in ['email', 'both']:
                        success = self.reporter.send_summary_email(html_content)
                        if success:
                            logger.success(f'✓ Résumé envoyé - {self.reporter.summary_folder}')
                    if SUMMARY_FORMAT in ['console', 'both']:
                        logger.info(f'📊 Résumé: {summary["urgent_count"]} urgent, {summary["high_count"]} high, {summary["medium_count"]} medium')
                    self.reporter.save_summary_locally(summary, html_content)
                    self.last_summary_hour = current_hour
                else:
                    logger.debug(f'Aucun message important à rapporter {current_hour}:00')
                    self.last_summary_hour = current_hour
        except Exception as e:
            logger.error(f'Erreur lors de la génération du résumé: {e}')


if __name__ == '__main__':
    try:
        processor = EmailProcessor()
        processor.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.critical(f'Crash fatal: {e}')
        sys.exit(1)
