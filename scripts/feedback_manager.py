#!/usr/bin/env python3
import email
from email.header import decode_header
from loguru import logger
from adaptive_learner import AdaptiveLearner

class FeedbackManager:
    def __init__(self, classifier, mailbox):
        self.classifier = classifier
        self.mailbox = mailbox
        self.learner = AdaptiveLearner() # Le cerveau

    def check_for_feedback(self):
        """Scanne les dossiers Training/* et Feedback/*."""
        try:
            _, folders = self.mailbox.client.list()
            for f in folders:
                name = f.decode().split(' "/" ')[-1].strip('"')

                # Détection des dossiers d'apprentissage
                if name.startswith("Training/") or name.startswith("Feedback/"):
                    category = name.split("/")[-1].upper()
                    # Vérifier si c'est une catégorie valide
                    if category in self.classifier.categories:
                        self._process_folder(name, category)
        except Exception as e:
            logger.error(f"Erreur feedback: {e}")

    def _process_folder(self, folder, category):
        try:
            self.mailbox.client.select(f'"{folder}"')
            _, ids = self.mailbox.client.search(None, 'ALL')
            if not ids[0]: return

            email_ids = ids[0].split()
            logger.info(f"🎓 Apprentissage ({category}): {len(email_ids)} emails")

            for e_id in email_ids:
                _, data = self.mailbox.client.fetch(e_id, '(RFC822)')
                msg = email.message_from_bytes(data[0][1])

                subject = self._decode(msg.get("Subject", ""))
                sender = self._decode(msg.get("From", ""))
                body_preview = "" # Pas besoin du body pour les règles simples

                # 1. Enregistrer la règle dans le cerveau
                self.learner.learn_from_correction(
                    email_id=e_id.decode(),
                    subject=subject,
                    sender=sender,
                    body_preview=body_preview,
                    wrong_category="UNKNOWN", # On ne sait pas ce que c'était avant
                    correct_category=category
                )

                # 2. Supprimer l'email (il a servi)
                self.mailbox.client.store(e_id, '+FLAGS', '\\Deleted')

            self.mailbox.client.expunge()
            logger.success(f"✓ Cerveau mis à jour avec {len(email_ids)} règles pour {category}")

        except Exception as e:
            logger.error(f"Erreur dossier {folder}: {e}")

    def _decode(self, header):
        try:
            parts = decode_header(header)
            return ''.join([str(p[0], p[1] or 'utf-8') if isinstance(p[0], bytes) else str(p[0]) for p in parts])
        except:
            return str(header)
