#!/usr/bin/env python3
# ============================================================================
# FEEDBACK MANAGER - ProtonLumoAI
# Apprentissage continu basé sur les corrections de l'utilisateur
# ============================================================================

import os
import time
import json
from pathlib import Path
from typing import List, Dict

from loguru import logger
import email
from email.message import Message
from email.header import decode_header

from email_classifier import EmailClassifier


class FeedbackManager:
    """Surveille les corrections de l'utilisateur et réentraîne le modèle."""

    def __init__(self, classifier: EmailClassifier, mailbox_client):
        """Initialise le gestionnaire de feedback."""
        self.classifier = classifier
        self.mailbox = mailbox_client
        self.feedback_folder = "À traiter"
        self.training_data_path = Path("../data/training_data.json").resolve()
        self.training_data = self._load_training_data()

    def _load_training_data(self) -> List[Dict]:
        """Charge les données d'entraînement depuis le fichier."""
        if self.training_data_path.exists():
            with open(self.training_data_path, "r") as f:
                return json.load(f)
        return []

    def _save_training_data(self):
        """Sauvegarde les données d'entraînement."""
        with open(self.training_data_path, "w") as f:
            json.dump(self.training_data, f, indent=2)

    def check_for_feedback(self):
        """Vérifie le dossier de feedback pour les corrections."""
        logger.info("Vérification du feedback de l'utilisateur...")
        
        try:
            # Lister tous les dossiers pour trouver les corrections
            status, folders = self.mailbox.client.list()
            if status != 'OK':
                return

            for folder_info in folders:
                folder_name = folder_info.decode().split(' "/" ')[-1].strip('"')
                
                # Si un email a été déplacé HORS du dossier "À traiter"
                # (cette logique est simplifiée, une vraie implémentation
                # nécessiterait de suivre les UID des emails)
                
                # Pour cette version, on va scanner un dossier "Feedback/Correct"
                if folder_name.startswith("Feedback/"):
                    self._process_feedback_folder(folder_name)

        except Exception as e:
            logger.error(f"Erreur lors de la vérification du feedback: {e}")

    def _process_feedback_folder(self, folder_name: str):
        """Traite un dossier de feedback pour l'entraînement."""
        try:
            self.mailbox.client.select(f'"{folder_name}"')
            status, messages = self.mailbox.client.search(None, 'ALL')
            if status != 'OK':
                return

            email_ids = messages[0].split()
            if not email_ids:
                return

            logger.info(f"Trouvé {len(email_ids)} emails de feedback dans {folder_name}")
            
            # La catégorie est le nom du sous-dossier
            correct_category = folder_name.split('/')[-1]

            new_examples_X = []
            new_examples_y = []

            for email_id in email_ids:
                status, msg_data = self.mailbox.client.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue

                msg = email.message_from_bytes(msg_data[0][1])
                subject = self._decode_header(msg["Subject"])
                body = self._get_body(msg)
                
                text = f"{subject} {self.classifier._clean_text(body)}"
                new_examples_X.append(text)
                new_examples_y.append(correct_category)
                
                # Supprimer l'email après l'entraînement
                self.mailbox.client.store(email_id, '+FLAGS', '\\Deleted')

            # Entraîner le modèle avec les nouveaux exemples
            self.classifier.train(new_examples_X, new_examples_y)
            
            self.mailbox.client.expunge()
            logger.success(f"Modèle réentraîné avec {len(new_examples_X)} exemples de la catégorie {correct_category}")

        except Exception as e:
            logger.error(f"Erreur traitement dossier feedback {folder_name}: {e}")

    def _decode_header(self, header: str) -> str:
        """Décode un en-tête d'email."""
        if header is None:
            return ""
        decoded_header = email.header.decode_header(header)
        return ' '.join([str(text, charset or 'utf-8') for text, charset in decoded_header])

    def _get_body(self, msg: email.message.Message) -> str:
        """Extrait le corps de l'email."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    return part.get_payload(decode=True).decode()
        else:
            return msg.get_payload(decode=True).decode()
        return ""
