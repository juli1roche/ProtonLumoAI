#!/usr/bin/env python3
# ============================================================================
# EMAIL PROCESSOR - ProtonLumoAI
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

from email_classifier import EmailClassifier
from email_parser import EmailParser
from feedback_manager import FeedbackManager

# ... (le reste du code reste le même jusqu'à la classe EmailProcessor)

class EmailProcessor:
    """Processeur principal pour le traitement des emails"""

    def __init__(self):
        """Initialise le processeur"""
        self.classifier = EmailClassifier()
        self.parser = EmailParser()
        self.feedback_manager = None
        self.running = False
        self.last_improvement = 0
        self.processed_count = 0
        self.error_count = 0
        
        logger.info("EmailProcessor initialisé avec le nouveau parser robuste")

    # ... (la méthode connect_mailbox reste la même)

    def process_folder(self, mailbox: ProtonMailBox, folder_name: str) -> int:
        """Traite un dossier spécifique de manière robuste."""
        processed = 0
        try:
            mailbox.client.select(f'"{folder_name}"')
            
            # ... (la recherche d'emails reste la même)

            for email_id in email_ids:
                try:
                    status, msg_data = mailbox.client.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue

                    # Utilisation du nouveau parser robuste
                    subject, sender, body = self.parser.parse(msg_data[0][1])

                    # Le classifieur reçoit maintenant des données propres et garanties
                    category, confidence = self.classifier.classify(subject, body)
                    logger.info(f"Email {email_id.decode()}: {category} (confiance: {confidence:.2f})")

                    # ... (la logique de déplacement reste la même)

                except Exception as e:
                    logger.error(f"Erreur irrécupérable traitement email {email_id}: {e}")
                    self.error_count += 1
            
            # ... (l'expunge reste le même)

        except Exception as e:
            logger.error(f"Erreur critique traitement dossier {folder_name}: {e}")
        
        return processed

    # ... (le reste des méthodes _get_target_folder, run_once, etc. restent les mêmes)
