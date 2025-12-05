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


class ProtonMailBox(MailBox):
    """MailBox personnalisé pour ProtonMail Bridge avec STARTTLS"""
    
    def __init__(self, host, port, username, password, timeout=None):
        """Initialise la connexion avec STARTTLS"""
        # Créer le contexte SSL
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Appeler le constructeur parent SANS ssl_context (pour éviter SSL direct)
        super().__init__(host=host, port=port, timeout=timeout)
        
        # Remplacer la connexion par une connexion STARTTLS
        try:
            # Créer une connexion IMAP4 non sécurisée
            self.client = imaplib.IMAP4(host, port, timeout=timeout or 10)
            # Appliquer STARTTLS
            self.client.starttls(ssl_context=ssl_context)
            # Se connecter
            self.client.login(username, password)
            logger.success(f"Connexion STARTTLS établie avec {host}:{port}")
        except Exception as e:
            logger.error(f"Erreur connexion STARTTLS: {e}")
            raise

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

    def process_inbox(self, mailbox: MailBox) -> int:
        """
        Traite la boîte de réception
        
        Returns:
            Nombre d'emails traités
        """
        logger.info("Traitement de la boîte de réception...")
        processed = 0
        
        try:
            mailbox.folder.set('INBOX')
            
            # Récupérer les emails non lus ou tous les emails
            if PROCESS_UNSEEN_ONLY:
                emails = mailbox.fetch(AND(seen=False), mark_seen=False)
            else:
                emails = mailbox.fetch()
            
            for email in emails:
                try:
                    # Classification
                    result = self.classifier.classify(
                        email_id=email.uid,
                        subject=email.subject or "(Sans sujet)",
                        body=email.text or email.html or ""
                    )
                    
                    logger.info(f"Email: {result.subject[:50]} -> {result.category} ({result.confidence:.2f})")
                    
                    # Déterminer le dossier cible
                    if result.category in self.classifier.categories:
                        target_folder = self.classifier.categories[result.category].folder
                    else:
                        target_folder = "À classer"
                    
                    # Déplacer l'email (sauf en dry-run)
                    if not DRY_RUN:
                        try:
                            # Vérifier que le dossier existe
                            if not mailbox.folder.exists(target_folder):
                                logger.warning(f"Création du dossier {target_folder}")
                                mailbox.folder.create(target_folder)
                            
                            mailbox.move(email.uid, target_folder)
                            logger.success(f"✓ Déplacé vers {target_folder}")
                        except Exception as e:
                            logger.error(f"Erreur déplacement: {e}")
                            self.error_count += 1
                    else:
                        logger.info(f"[DRY-RUN] Serait déplacé vers {target_folder}")
                    
                    processed += 1
                
                except Exception as e:
                    logger.error(f"Erreur traitement email {email.uid}: {e}")
                    self.error_count += 1
        
        except Exception as e:
            logger.error(f"Erreur accès inbox: {e}")
        
        self.processed_count += processed
        logger.info(f"Traitement terminé: {processed} email(s) traité(s)")
        return processed

    def check_improvements(self, mailbox: MailBox):
        """Vérifie et applique les améliorations automatiques"""
        current_time = time.time()
        
        if current_time - self.last_improvement < AUTO_IMPROVE_INTERVAL:
            return
        
        logger.info("Démarrage de l'amélioration automatique...")
        try:
            report = self.trainer.auto_improve(mailbox)
            
            if report["status"] == "success":
                logger.success(f"Amélioration complétée: {json.dumps(report, ensure_ascii=False, default=str)}")
            else:
                logger.error(f"Erreur amélioration: {report.get('error')}")
            
            self.last_improvement = current_time
        
        except Exception as e:
            logger.error(f"Erreur amélioration: {e}")

    def run_once(self) -> bool:
        """Exécute un cycle de traitement"""
        try:
            with self.connect_mailbox() as mailbox:
                # Traiter l'inbox
                self.process_inbox(mailbox)
                
                # Vérifier les améliorations
                self.check_improvements(mailbox)
                
                return True
        
        except Exception as e:
            logger.error(f"Erreur cycle: {e}")
            return False

    def run_loop(self):
        """Boucle principale de traitement"""
        logger.info("Démarrage de la boucle de traitement...")
        self.running = True
        
        while self.running:
            try:
                logger.info(f"Cycle de traitement (intervalle: {POLL_INTERVAL}s)")
                
                if self.run_once():
                    logger.info(f"Pause de {POLL_INTERVAL}s...")
                    time.sleep(POLL_INTERVAL)
                else:
                    logger.warning("Erreur cycle, retry dans 10s...")
                    time.sleep(10)
            
            except KeyboardInterrupt:
                logger.info("Arrêt demandé par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"Erreur boucle: {e}")
                time.sleep(30)

    def stop(self):
        """Arrête le processeur"""
        logger.info("Arrêt du processeur...")
        self.running = False

    def get_status(self) -> Dict:
        """Retourne le statut du processeur"""
        return {
            "running": self.running,
            "processed": self.processed_count,
            "errors": self.error_count,
            "classifier_stats": self.classifier.get_statistics(),
            "trainer_stats": self.trainer.get_summary()
        }


def signal_handler(signum, frame):
    """Gestionnaire de signaux"""
    logger.info(f"Signal reçu: {signum}")
    if processor:
        processor.stop()
    sys.exit(0)


def main():
    """Point d'entrée principal"""
    global processor
    
    # Vérifier les variables d'environnement
    if not IMAP_USERNAME or not IMAP_PASSWORD:
        logger.error("PROTON_USERNAME et PROTON_PASSWORD doivent être définis")
        logger.error("Exemple: export PROTON_USERNAME='user@proton.me'")
        logger.error("         export PROTON_PASSWORD='bridge_password'")
        sys.exit(1)
    
    # Configuration des signaux
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Démarrer le processeur
    processor = EmailProcessor()
    
    logger.info("=" * 60)
    logger.info("ProtonLumoAI - Processeur d'Emails")
    logger.info("=" * 60)
    logger.info(f"Bridge: {IMAP_HOST}:{IMAP_PORT}")
    logger.info(f"Intervalle de polling: {POLL_INTERVAL}s")
    logger.info(f"Intervalle d'amélioration: {AUTO_IMPROVE_INTERVAL}s")
    logger.info(f"Emails non-lus uniquement: {PROCESS_UNSEEN_ONLY}")
    logger.info(f"Mode dry-run: {DRY_RUN}")
    logger.info("=" * 60)
    
    # Lancer la boucle
    try:
        processor.run_loop()
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)
    finally:
        logger.info("Processeur arrêté")


if __name__ == "__main__":
    main()
