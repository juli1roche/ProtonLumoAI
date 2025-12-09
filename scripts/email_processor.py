#!/usr/bin/env python3
# ============================================================================
# EMAIL PROCESSOR - ProtonLumoAI
# Fix: Batch Result Key Matching & Debugging
# ============================================================================

import os
import time
import signal
import sys
import ssl
import imaplib
import json
from pathlib import Path
from typing import Optional, Set, Dict, List, Tuple
from datetime import datetime, timedelta
import email.utils
import threading
import re

# === PERFORMANCE OPTIMIZATIONS (v1.2.0) ===
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    """Wrapper IMAP pour ProtonMail Bridge gérant STARTTLS."""
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
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            self.client = imaplib.IMAP4(self.host, self.port, timeout=self.timeout)
            self.client.starttls(ssl_context=ssl_context)
            self.client.login(self.username, self.password)
            logger.success(f"Connexion établie ({self.host}:{self.port})")
            self._refresh_folder_cache()
        except Exception as e:
            logger.error(f"Échec connexion IMAP: {e}")
            if self.client:
                try: self.client.logout()
                except: pass
            raise

    def _refresh_folder_cache(self):
        try:
            status, folders = self.client.list()
            if status == 'OK':
                for folder_bytes in folders:
                    try: folder_raw = folder_bytes.decode('utf-8')
                    except: folder_raw = folder_bytes.decode('latin-1')
                    parts = folder_raw.split('"')
                    if len(parts) >= 3:
                        self._existing_folders.add(parts[-2])
        except Exception as e:
            logger.warning(f"Erreur cache dossiers: {e}")

    def folder_exists(self, folder_path: str) -> bool:
        return folder_path in self._existing_folders

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.close()

    def close(self):
        if self.client:
            try: self.client.close()
            except: pass
            try: self.client.logout()
            except: pass


class EmailProcessor:
    """Processeur principal."""

    def __init__(self):
        self.classifier = EmailClassifier()
        self.parser = EmailParser()
        self.feedback_manager: Optional[FeedbackManager] = None
        self.running = True

        if SUMMARY_ENABLED:
            self.detector = ImportantMessageDetector()
            self.reporter = None
            self.last_summary_hour = -1
            logger.info(f"✨ Executive Summary ACTIVÉ - {SUMMARY_HOURS}h")
        else:
            self.detector = None
            self.reporter = None

        # Optimization settings
        self.enable_parallel = os.getenv("PROTON_LUMO_ENABLE_PARALLEL", "true").lower() == "true"
        self.max_workers = int(os.getenv("PROTON_LUMO_MAX_WORKERS", 5))
        self.enable_batch = os.getenv("PROTON_LUMO_ENABLE_BATCH", "true").lower() == "true"
        self.batch_size = int(os.getenv("PROTON_LUMO_BATCH_SIZE", 10))
        self.metrics_enabled = os.getenv("PROTON_LUMO_METRICS_ENABLED", "true").lower() == "true"

        if self.enable_parallel:
            self.parallel_processor = ParallelProcessor(max_workers=self.max_workers, enable_metrics=self.metrics_enabled)
        else:
            self.parallel_processor = None

        if self.enable_batch:
            self.batch_classifier = BatchClassifier(enable_batch=True, batch_size=self.batch_size)
        else:
            self.batch_classifier = None

        logger.info(f"Optimizations: Parallel={self.enable_parallel}, Batch={self.enable_batch} (size={self.batch_size})")

        self.checkpoint = self._load_checkpoint()
        self.initial_scan_done = self.checkpoint.get('initial_scan_done', False)
        self.last_check: Dict[str, str] = self.checkpoint.get('last_check', {})
        self.processed_emails: Set[str] = set(self.checkpoint.get('processed_emails', []))

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_checkpoint(self) -> dict:
        if CHECKPOINT_FILE.exists():
            try:
                with open(CHECKPOINT_FILE, 'r') as f: return json.load(f)
            except: pass
        return {}

    def _save_checkpoint(self):
        try:
            data = {
                'initial_scan_done': self.initial_scan_done,
                'last_check': self.last_check,
                'processed_emails': list(self.processed_emails),
                'last_update': datetime.now().isoformat()
            }
            with open(CHECKPOINT_FILE, 'w') as f: json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur save checkpoint: {e}")

    def _signal_handler(self, sig, frame):
        logger.info("Arrêt demandé...")
        self._save_checkpoint()
        self.running = False

    def connect_mailbox(self) -> ProtonMailBox:
        return ProtonMailBox(PROTON_BRIDGE_HOST, PROTON_BRIDGE_PORT, PROTON_USERNAME, PROTON_PASSWORD)

    def _get_target_folder(self, category: str) -> Optional[str]:
        if category == "UNKNOWN": return None
        cat = self.classifier.categories.get(category)
        return cat.folder if cat else None

    def ensure_folder_exists(self, mailbox: ProtonMailBox, folder_path: str) -> bool:
        if mailbox.folder_exists(folder_path): return True
        path_parts = folder_path.split('/')
        current = ''
        for part in path_parts:
            current = f"{current}/{part}" if current else part
            if not mailbox.folder_exists(current):
                try:
                    mailbox.client.create(f'"{current}"')
                    mailbox._existing_folders.add(current)
                except: return False
        return True

    def _get_email_date(self, mailbox: ProtonMailBox, email_id: bytes) -> datetime:
        try:
            res, data = mailbox.client.fetch(email_id, '(INTERNALDATE)')
            if res == 'OK' and data[0]:
                date_str = data[0].decode('utf-8', errors='ignore')
                match = re.search(r'"([^"]+)"', date_str)
                if match:
                    dt = email.utils.parsedate_tz(match.group(1))
                    if dt: return datetime.fromtimestamp(email.utils.mktime_tz(dt))
        except: pass
        return datetime.min

    def _sort_emails_by_date(self, mailbox: ProtonMailBox, email_ids: List[bytes], limit: int) -> List[bytes]:
        if not email_ids or len(email_ids) <= limit: return email_ids
        logger.debug(f"Tri de {len(email_ids)} emails...")
        dated = [(eid, self._get_email_date(mailbox, eid)) for eid in email_ids]
        dated.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in dated[:limit]]

    def _score_and_track_message(self, uid, sender, subject, body, category, confidence):
        if not self.detector: return
        try:
            score, breakdown, action = self.detector.score_message(uid, sender, subject, body, category, confidence)
            if score >= SUMMARY_MIN_SCORE:
                msg = ImportantMessage(uid, sender, subject[:100], score, category, breakdown, action, "new", datetime.now().isoformat(), confidence)
                self.detector.save_important_message(msg)
                logger.debug(f"📊 Important ({score}): {subject[:30]}...")
        except: pass

    def _check_and_send_summary(self, mailbox: ProtonMailBox):
        if not self.detector or not self.reporter: return
        try:
            now = datetime.now().hour
            if now in SUMMARY_HOURS and now != self.last_summary_hour:
                logger.info(f"🔔 Generating Executive Summary ({now}h)")
                msgs = self.detector._load_important_messages()
                if msgs:
                    summary = self.detector.generate_executive_summary(msgs)
                    html = self.reporter.generate_html_report(summary)
                    if SUMMARY_FORMAT in ["email", "both"]: self.reporter.send_summary_email(html)
                    self.reporter.save_summary_locally(summary, html)
                self.last_summary_hour = now
        except Exception as e: logger.error(f"Summary error: {e}")

    def _classify_batch(self, email_ids: List[bytes], mailbox) -> Dict[str, Tuple[str, float]]:
        """Optimized batch classification with fixed key types."""
        if not self.enable_batch or not self.batch_classifier: return {}

        logger.info(f"🚀 Batching {len(email_ids)} emails...")
        batch_emails = []
        for eid in email_ids:
            try:
                res, data = mailbox.client.fetch(eid, '(RFC822)')
                if res == 'OK':
                    # IMPORTANT: uid passed to BatchEmail MUST be string
                    uid_str = eid.decode('utf-8')
                    subj, sender, body = self.parser.parse(data[0][1])
                    batch_emails.append(BatchEmail(uid_str, subj, body[:500]))
            except: continue

        if not batch_emails: return {}

        results = {}
        valid_cats = list(self.classifier.categories.keys())
        for i in range(0, len(batch_emails), self.batch_size):
            chunk = batch_emails[i:i + self.batch_size]
            # Assumes classify_batch returns dict {uid: {'category':..., 'confidence':...}}
            results.update(self.batch_classifier.classify_batch(chunk, valid_cats))

        # FIXED: Ensure keys are strictly strings matching email_uid format
        formatted = {}
        for uid, data in results.items():
            formatted[str(uid)] = (data['category'], data['confidence'])

        logger.info(f"✅ Batch result: {len(formatted)} emails classified. Keys sample: {list(formatted.keys())[:3]}")
        return formatted

    def process_folder(self, mailbox: ProtonMailBox, folder_name: str = "INBOX") -> int:
        processed_count = 0
        try:
            try: mailbox.client.select(f'"{folder_name}"')
            except: return 0

            criteria = 'UNSEEN' if UNSEEN_ONLY else 'ALL'
            status, messages = mailbox.client.search(None, criteria)
            if status != 'OK' or not messages[0]: return 0

            email_ids = messages[0].split()

            # Limits
            limit = SPAM_TRASH_LIMIT if any(x in folder_name.lower() for x in ['spam', 'trash']) else MAX_EMAILS_PER_FOLDER
            if len(email_ids) > limit:
                email_ids = self._sort_emails_by_date(mailbox, email_ids, limit)

            logger.info(f"Processing {len(email_ids)} emails in {folder_name}")

            # === BATCH ===
            batch_results = {}
            if self.enable_batch and len(email_ids) > 1:
                to_process = [eid for eid in email_ids if f"{folder_name}:{eid.decode()}" not in self.processed_emails]
                if to_process:
                    batch_results = self._classify_batch(to_process, mailbox)

            # === PROCESS ===
            for eid in email_ids:
                if not self.running: break

                uid = eid.decode('utf-8')
                key = f"{folder_name}:{uid}"
                if key in self.processed_emails: continue

                try:
                    res, flags = mailbox.client.fetch(eid, '(FLAGS)')
                    was_seen = b'\\Seen' in flags[0] if res == 'OK' else False

                    # Check Batch Result
                    if uid in batch_results:
                        category, confidence = batch_results[uid]
                        # Fetch header only for context/logging
                        res, data = mailbox.client.fetch(eid, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])')
                        raw_header = data[0][1] if res == 'OK' else b''
                        msg = email.message_from_bytes(raw_header)
                        subject = msg['Subject'] or "Unknown"
                        sender = msg['From'] or "Unknown"
                        body = "Batch processed"
                        logger.info(f"⚡ Batch Hit: '{subject[:30]}...' -> {category}")
                    else:
                        # Fallback
                        if self.enable_batch and len(email_ids) > 1:
                            logger.debug(f"⚠️ Batch miss for UID {uid}. Available keys: {list(batch_results.keys())[:5]}")

                        res, data = mailbox.client.fetch(eid, '(RFC822)')
                        if res != 'OK': continue
                        subj, sender, body = self.parser.parse(data[0][1])
                        res_cls = self.classifier.classify(uid, subj, body)
                        category, confidence = res_cls.category, res_cls.confidence
                        subject = subj
                        logger.info(f"🐢 Standard: '{subject[:30]}...' -> {category}")

                    if SUMMARY_ENABLED:
                        self._score_and_track_message(uid, sender, subject, body, category, confidence)

                    target = self._get_target_folder(category)
                    if target and not DRY_RUN:
                        if self.ensure_folder_exists(mailbox, target):
                            res, _ = mailbox.client.copy(eid, f'"{target}"')
                            if res == 'OK':
                                mailbox.client.store(eid, '+FLAGS', '\\Deleted')
                                logger.success(f"Moved to {target}")
                                processed_count += 1
                                self.processed_emails.add(key)
                    else:
                        self.processed_emails.add(key)

                except Exception as e:
                    logger.error(f"Error on email {uid}: {e}")

            if not DRY_RUN and processed_count > 0:
                mailbox.client.expunge()
            self.last_check[folder_name] = datetime.now().isoformat()

        except Exception as e: logger.error(f"Folder error {folder_name}: {e}")
        return processed_count

    def run(self):
        logger.info("Service started.")
        while self.running:
            try:
                with self.connect_mailbox() as mb:
                    if SUMMARY_ENABLED and not self.reporter: self.reporter = SummaryEmailReporter(mb)
                    if not self.feedback_manager: self.feedback_manager = FeedbackManager(self.classifier, mb)

                    status, folders = mb.client.list()
                    if status == 'OK':
                        for f in folders:
                            name = f.decode().split('"')[-2]
                            if name not in ["All Mail", "Trash", "Sent"] and not name.startswith("["):
                                self.process_folder(mb, name)

                    self._check_and_send_summary(mb)
                    self._save_checkpoint()
                    if not self.initial_scan_done:
                        self.initial_scan_done = True
                        self._save_checkpoint()

                time.sleep(POLL_INTERVAL)
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(10)

if __name__ == "__main__":
    EmailProcessor().run()

