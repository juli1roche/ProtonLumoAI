#!/usr/bin/env python3
# ============================================================================
# EMAIL PROCESSOR - ProtonLumoAI
# Traitement automatique des emails ProtonMail avec classification intelligente
# ============================================================================

import os
import time
import json
import signal
import sys
import ssl
import imaplib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from threading import Thread, Event

from loguru import logger
from imap_tools import MailBox, AND

from email_classifier import EmailClassifier
from train_classifier import TrainingManager


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


# --- CONFIGURATION LOGGING ---
LOG_DIR = Path(os.getenv("PROTON_LUMO_LOGS", "~/ProtonLumoAI/logs")).expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger.add(LOG_DIR / "processor.log", rotation="10 MB", retention="30 days")

# --- CONFIGURATION IMAP ---
IMAP_HOST = os.getenv("PROTON_BRIDGE_HOST", "127.0.0.1")
IMAP_PORT = int(os.getenv("PROTON_BRIDGE_PORT", "1143"))
IMAP_USERNAME = os.getenv("PROTON_USERNAME", "")
IMAP_PASSWORD = os.getenv("PROTON_PASSWORD", "")

# --- CONFIGURATION DE TRAITEMENT ---
POLL_INTERVAL = int(os.getenv("PROTON_LUMO_POLL_INTERVAL", "60"))  # secondes
AUTO_IMPROVE_INTERVAL = int(os.getenv("PROTON_LUMO_AUTO_IMPROVE_INTERVAL", "3600"))  # 1 heure
PROCESS_UNSEEN_ONLY = os.getenv("PROTON_LUMO_UNSEEN_ONLY", "true").lower() == "true"
DRY_RUN = os.getenv("PROTON_LUMO_DRY_RUN", "false").lower() == "true"

# --- DOSSIERS SPÉCIAUX ---
TRAINING_FOLDER_ROOT = "Training"
FEEDBACK_FOLDER = "Feedback"


class EmailProcessor:
    """Processeur principal pour le traitement des emails"""

    def __init__(self):
        """Initialise le processeur"""
        self.classifier = EmailClassifier()
        self.trainer = TrainingManager(self.classifier)
        self.running = False
        self.last_improvement = 0
        self.processed_count = 0
        self.error_count = 0
        
        logger.info("EmailProcessor initialisé")

    def connect_mailbox(self) -> ProtonMailBox:
        """Établit la connexion à la boîte mail ProtonMail Bridge"""
        logger.info(f"Connexion à {IMAP_HOST}:{IMAP_PORT}...")
        try:
            mailbox = ProtonMailBox(
                host=IMAP_HOST,
                port=IMAP_PORT,
                username=IMAP_USERNAME,
                password=IMAP_PASSWORD
            )
            logger.success("Connexion établie")
            return mailbox
        except Exception as e:
            logger.error(f"Erreur connexion: {e}")
            raise

    def process_inbox(self, mailbox: ProtonMailBox) -> int:
        """
        Traite la boîte de réception
        
        Returns:
            Nombre d'emails traités
        """
        logger.info("Traitement de la boîte de réception...")
        processed = 0
        
        try:
            # Sélectionner la boîte INBOX
            mailbox.client.select('INBOX')
            
            # Récupérer les emails non lus ou tous les emails
            if PROCESS_UNSEEN_ONLY:
                status, messages = mailbox.client.search(None, 'UNSEEN')
            else:
                status, messages = mailbox.client.search(None, 'ALL')
            
            if status != 'OK':
                logger.error(f"Erreur lors de la recherche d'emails: {status}")
                return 0
            
            email_ids = messages[0].split()
            logger.info(f"Trouvé {len(email_ids)} emails")
            
            # Traiter chaque email
            for email_id in email_ids:
                try:
                    # Récupérer l'email
                    status, msg_data = mailbox.client.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    msg = msg_data[0][1]
                    
                    # Classifier l'email
                    category = self.classifier.classify(msg)
                    logger.info(f"Email {email_id.decode()}: {category}")
                    
                    # Déplacer l'email vers le dossier approprié
                    if not DRY_RUN:
                        folder_name = self._get_folder_name(category)
                        mailbox.client.copy(email_id, folder_name)
                        mailbox.client.store(email_id, '+FLAGS', '\\Deleted')
                    
                    processed += 1
                except Exception as e:
                    logger.error(f"Erreur traitement email {email_id}: {e}")
                    self.error_count += 1
            
            # Expurger les emails supprimés
            if not DRY_RUN:
                mailbox.client.expunge()
            
            logger.success(f"Traitement terminé: {processed} emails traités")
            self.processed_count += processed
            
        except Exception as e:
            logger.error(f"Erreur traitement boîte: {e}")
        
        return processed

    def _get_folder_name(self, category: str) -> str:
        """Retourne le nom du dossier pour une catégorie"""
        folder_mapping = {
            "SPAM": "Spam",
            "VENTE": "Achats",
            "BANQUE": "Administratif/Banque",
            "PRO": "Travail",
            "URGENT": "À traiter",
            "VOYAGES": "Voyages",
            "SOCIAL": "Réseaux sociaux",
            "NEWSLETTER": "Newsletters"
        }
        return folder_mapping.get(category, "INBOX")

    def run_once(self) -> bool:
        """Exécute un cycle de traitement"""
        try:
            mailbox = self.connect_mailbox()
            try:
                self.process_inbox(mailbox)
            finally:
                mailbox.close()
            
            # Vérifier si amélioration automatique est nécessaire
            current_time = time.time()
            if current_time - self.last_improvement > AUTO_IMPROVE_INTERVAL:
                logger.info("Lancement de l'amélioration automatique...")
                self.trainer.auto_improve()
                self.last_improvement = current_time
            
            return True
        except Exception as e:
            logger.error(f"Erreur cycle: {e}")
            self.error_count += 1
            return False

    def run_loop(self, interval: int = POLL_INTERVAL):
        """Boucle de traitement continue"""
        logger.info("Démarrage de la boucle de traitement...")
        
        while self.running:
            logger.info(f"Cycle de traitement (intervalle: {interval}s)")
            
            if not self.run_once():
                logger.warning(f"Erreur cycle, retry dans 10s...")
                time.sleep(10)
            else:
                time.sleep(interval)

    def start(self):
        """Démarre le processeur"""
        self.running = True
        self.run_loop()

    def stop(self):
        """Arrête le processeur"""
        self.running = False
        logger.info("Arrêt du processeur...")

    def signal_handler(self, signum, frame):
        """Gestionnaire de signaux"""
        logger.info(f"Signal reçu: {signum}")
        self.stop()
        sys.exit(0)


def main():
    """Fonction principale"""
    processor = EmailProcessor()
    
    # Configurer les gestionnaires de signaux
    signal.signal(signal.SIGINT, processor.signal_handler)
    signal.signal(signal.SIGTERM, processor.signal_handler)
    
    # Afficher la configuration
    logger.info("=" * 60)
    logger.info("ProtonLumoAI - Processeur d'Emails")
    logger.info("=" * 60)
    logger.info(f"Bridge: {IMAP_HOST}:{IMAP_PORT}")
    logger.info(f"Intervalle de polling: {POLL_INTERVAL}s")
    logger.info(f"Intervalle d'amélioration: {AUTO_IMPROVE_INTERVAL}s")
    logger.info(f"Emails non-lus uniquement: {PROCESS_UNSEEN_ONLY}")
    logger.info(f"Mode dry-run: {DRY_RUN}")
    logger.info("=" * 60)
    
    # Démarrer le processeur
    processor.start()


if __name__ == "__main__":
    main()
