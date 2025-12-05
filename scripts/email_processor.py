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

class ProtonMailBox:
    """MailBox personnalisé pour ProtonMail Bridge avec STARTTLS"""
    
    def __init__(self, host, port, username, password, timeout=None):
        """Initialise la connexion avec STARTTLS"""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout or 10
        self.client = None
        
        # Établir la connexion
        self._connect()
    
    def _connect(self):
        """Établit la connexion STARTTLS avec ProtonMail Bridge"""
        try:
            # Créer le contexte SSL pour accepter les certificats auto-signés
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Créer une connexion IMAP4 non sécurisée d'abord
            logger.debug(f"Création connexion IMAP4 à {self.host}:{self.port}")
            self.client = imaplib.IMAP4(self.host, self.port, timeout=self.timeout)
            
            # Appliquer STARTTLS
            logger.debug("Envoi commande STARTTLS")
            response = self.client.starttls(ssl_context=ssl_context)
            logger.debug(f"Réponse STARTTLS: {response}")
            
            # Se connecter avec les credentials
            logger.debug(f"Authentification avec {self.username}")
            response = self.client.login(self.username, self.password)
            logger.debug(f"Réponse LOGIN: {response}")
            
            logger.success(f"Connexion STARTTLS établie avec {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Erreur connexion STARTTLS: {e}")
            if self.client:
                try:
                    self.client.close()
                except:
                    pass
            raise
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
    
    def close(self):
        """Ferme la connexion"""
        if self.client:
            try:
                self.client.close()
            except:
                pass

# ... (le reste du code reste le même)

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
            mailbox.client.select(f'\""{folder_name}\""')
            
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
