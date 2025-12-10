#!/usr/bin/env python3
# ============================================================================
# EMAIL PROCESSOR - ProtonLumoAI v2.1 (Bugfix Release)
# Fixes: Stale connection in FeedbackManager loop
# ============================================================================

import os
import time
import signal
import sys
import ssl
import imaplib
from typing import List, Dict

from loguru import logger
from dotenv import load_dotenv

# Imports locaux dynamiques
try:
    from email_classifier import EmailClassifier
    from email_classifier_batch import BatchClassifier, BatchEmail
    from email_parser import EmailParser
    from feedback_manager import FeedbackManager
    from adaptive_learner import AdaptiveLearner
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from email_classifier import EmailClassifier
    from email_classifier_batch import BatchClassifier, BatchEmail
    from email_parser import EmailParser
    from feedback_manager import FeedbackManager
    from adaptive_learner import AdaptiveLearner

load_dotenv()

# --- CONFIGURATION ---
PROTON_BRIDGE_HOST = os.getenv("PROTON_BRIDGE_HOST", "127.0.0.1")
PROTON_BRIDGE_PORT = int(os.getenv("PROTON_BRIDGE_PORT", 1143))
PROTON_USERNAME = os.getenv("PROTON_USERNAME")
PROTON_PASSWORD = os.getenv("PROTON_PASSWORD")
POLL_INTERVAL = int(os.getenv("PROTON_LUMO_POLL_INTERVAL", 60))
UNSEEN_ONLY = os.getenv("PROTON_LUMO_UNSEEN_ONLY", "true").lower() == "true"
DRY_RUN = os.getenv("PROTON_LUMO_DRY_RUN", "false").lower() == "true"
BATCH_SIZE = 10

# Dossiers techniques à exclure
SKIP_FOLDERS = [
    "[Imap]", "Labels/[Imap]", "Labels/[Imap]/Trash", "Labels/[Imap]/Sent",
    "All Mail", "Tous les messages", "Spam", "Trash", "Corbeille", "Bin",
    "Sent", "Envoyés", "Brouillons", "Drafts", "Archive"
]

class ProtonMailBox:
    """Wrapper IMAP optimisé pour Proton Bridge."""
    def __init__(self):
        self.client = None

    def connect(self):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            logger.debug(f"Connexion {PROTON_BRIDGE_HOST}:{PROTON_BRIDGE_PORT}...")
            self.client = imaplib.IMAP4(PROTON_BRIDGE_HOST, PROTON_BRIDGE_PORT)
            self.client.starttls(ssl_context=ctx)
            self.client.login(PROTON_USERNAME, PROTON_PASSWORD)
            logger.success("✓ Connexion IMAP établie")
            return self
        except Exception as e:
            logger.error(f"Erreur connexion: {e}")
            raise

    def close(self):
        if self.client:
            try:
                self.client.logout()
            except:
                pass

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class EmailProcessor:
    def __init__(self):
        self.classifier = EmailClassifier()
        self.batch_classifier = BatchClassifier(enable_batch=True, batch_size=BATCH_SIZE)
        self.parser = EmailParser()
        self.learner = AdaptiveLearner()
        self.feedback_manager = None
        self.running = True

        signal.signal(signal.SIGINT, self._stop)
        logger.info(f"🚀 ProtonLumoAI v2.1 Démarré [Batching: {BATCH_SIZE} | Learning: Actif]")

    def _stop(self, sig, frame):
        logger.warning("Arrêt demandé...")
        self.running = False

    def _get_target_folder(self, category: str) -> str:
        cat_obj = self.classifier.categories.get(category)
        return cat_obj.folder if cat_obj else None

    def process_batch(self, mailbox, batch_data: List[Dict], folder_name: str):
        unknown_emails = []
        actions = []

        for item in batch_data:
            sender = item['sender']
            subject = item['subject']
            uid = item['uid']

            # Mémoire
            prediction = self.learner.predict_from_rules(sender, subject)

            if prediction:
                category, conf = prediction
                logger.info(f"🧠 Mémoire: {subject[:30]}... -> {category}")
                actions.append({'uid': uid, 'category': category})
            else:
                unknown_emails.append(BatchEmail(
                    email_id=uid,
                    subject=subject,
                    body=item['body']
                ))

        # IA Batch
        if unknown_emails:
            valid_cats = list(self.classifier.categories.keys())
            logger.info(f"🤖 IA Batch: Classification de {len(unknown_emails)} emails...")
            results = self.batch_classifier.classify_batch(unknown_emails, valid_cats)

            for uid, res in results.items():
                category = res['category']
                logger.info(f"✨ IA: Email {uid} -> {category} ({res['confidence']:.2f})")
                actions.append({'uid': uid, 'category': category})

        # Déplacements
        moved_count = 0
        for action in actions:
            uid = action['uid']
            category = action['category']
            target_folder = self._get_target_folder(category)

            if target_folder and target_folder != folder_name:
                if not DRY_RUN:
                    try:
                        if not self._folder_exists(mailbox, target_folder):
                            mailbox.client.create(f'"{target_folder}"')

                        res, _ = mailbox.client.copy(uid.encode(), f'"{target_folder}"')
                        if res == 'OK':
                            mailbox.client.store(uid.encode(), '+FLAGS', '\\Deleted')
                            logger.success(f"✓ Déplacé vers {target_folder}")
                            moved_count += 1
                    except Exception as e:
                        logger.error(f"Erreur déplacement {uid}: {e}")
                else:
                    logger.info(f"[DRY-RUN] Vers {target_folder}")

        return moved_count

    def _folder_exists(self, mailbox, folder):
        return True

    def process_folder(self, mailbox, folder_name):
        try:
            typ, _ = mailbox.client.select(f'"{folder_name}"')
            if typ != 'OK': return 0

            criteria = 'UNSEEN' if UNSEEN_ONLY else 'ALL'
            typ, msg_ids = mailbox.client.search(None, criteria)
            if typ != 'OK' or not msg_ids[0]: return 0

            email_ids = msg_ids[0].split()
            total = len(email_ids)
            logger.info(f"📂 {folder_name}: {total} emails à traiter")

            processed_total = 0
            current_batch = []

            for i, e_id in enumerate(email_ids):
                if not self.running: break

                try:
                    _, data = mailbox.client.fetch(e_id, '(RFC822)')
                    raw = data[0][1]
                    parsed = self.parser.parse(raw)

                    current_batch.append({
                        'uid': e_id.decode(),
                        'subject': parsed[0],
                        'sender': parsed[1],
                        'body': parsed[2]
                    })

                    if len(current_batch) >= BATCH_SIZE or i == total - 1:
                        processed_total += self.process_batch(mailbox, current_batch, folder_name)
                        current_batch = []

                except Exception as e:
                    logger.error(f"Erreur fetch {e_id}: {e}")

            if processed_total > 0 and not DRY_RUN:
                mailbox.client.expunge()

            return processed_total

        except Exception as e:
            logger.error(f"Erreur dossier {folder_name}: {e}")
            return 0

    def run(self):
        while self.running:
            try:
                # Nouvelle connexion à chaque cycle
                with ProtonMailBox() as mailbox:

                    # CORRECTION CRITIQUE ICI : Mise à jour de la mailbox pour le feedback
                    if not self.feedback_manager:
                        self.feedback_manager = FeedbackManager(self.classifier, mailbox)
                    else:
                        self.feedback_manager.mailbox = mailbox  # <--- C'est la ligne qui manquait !

                    # Apprentissage
                    self.feedback_manager.check_for_feedback()

                    # Scan des dossiers
                    _, folders = mailbox.client.list()
                    for f in folders:
                        raw_name = f.decode()
                        name = raw_name.split(' "/" ')[-1].strip('"')

                        if any(skip in name for skip in SKIP_FOLDERS): continue
                        if name.startswith("Training") or name.startswith("Feedback"): continue

                        self.process_folder(mailbox, name)

                time.sleep(POLL_INTERVAL)
            except Exception as e:
                logger.error(f"Erreur boucle principale: {e}")
                time.sleep(10)

if __name__ == "__main__":
    EmailProcessor().run()
