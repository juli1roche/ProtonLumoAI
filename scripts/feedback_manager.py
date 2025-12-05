#!/usr/bin/env python3
# ============================================================================
# FEEDBACK MANAGER - ProtonLumoAI (Version Corrigée)
# ============================================================================

import email
from email.header import decode_header
from loguru import logger
from email_classifier import EmailClassifier

class FeedbackManager:
    """Surveille les corrections de l'utilisateur et améliore le modèle."""

    def __init__(self, classifier: EmailClassifier, mailbox_client):
        self.classifier = classifier
        self.mailbox = mailbox_client

    def check_for_feedback(self):
        """Vérifie les dossiers de feedback."""
        try:
            status, folders = self.mailbox.client.list()
            if status != 'OK': return

            for folder_info in folders:
                folder_name = folder_info.decode().split(' "/" ')[-1].strip('"')
                if folder_name.startswith("Feedback/") or folder_name.startswith("Training/"):
                    self._process_feedback_folder(folder_name)

        except Exception as e:
            logger.error(f"Erreur check feedback: {e}")

    def _process_feedback_folder(self, folder_name: str):
        try:
            self.mailbox.client.select(f'"{folder_name}"')
            status, messages = self.mailbox.client.search(None, 'ALL')
            if status != 'OK' or not messages[0]: return

            email_ids = messages[0].split()
            correct_category = folder_name.split('/')[-1].upper()

            if correct_category not in self.classifier.categories:
                logger.warning(f"Catégorie inconnue dans le feedback: {correct_category}")
                return

            logger.info(f"Apprentissage : {len(email_ids)} emails trouvés dans {folder_name}")

            for email_id in email_ids:
                status, msg_data = self.mailbox.client.fetch(email_id, '(RFC822)')
                if status != 'OK': continue

                msg = email.message_from_bytes(msg_data[0][1])
                subject = self._decode_header(msg.get("Subject", ""))
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors='ignore')
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore')

                self.classifier.add_training_example(
                    email_id=email_id.decode(),
                    subject=subject,
                    body=body,
                    category=correct_category,
                    user_corrected=True
                )
                
                if self.classifier.use_lumo:
                    self.classifier.train_lumo(correct_category, [f"{subject} {body[:500]}"])

                self.mailbox.client.store(email_id, '+FLAGS', '\\Deleted')

            self.mailbox.client.expunge()
            logger.success(f"✓ Modèle mis à jour avec {len(email_ids)} exemples pour {correct_category}")

        except Exception as e:
            logger.error(f"Erreur traitement dossier {folder_name}: {e}")

    def _decode_header(self, header):
        try:
            parts = decode_header(header)
            return ''.join([str(p[0], p[1] or 'utf-8') if isinstance(p[0], bytes) else str(p[0]) for p in parts])
        except:
            return str(header)
