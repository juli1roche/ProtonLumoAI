#!/usr/bin/env python3
# ============================================================================
# SYNC & LEARN - ProtonLumoAI v1.3.0
# Synchronise les dossiers et analyse les patterns pour apprentissage
# ============================================================================

import os
import sys
import imaplib
import email
from pathlib import Path
from typing import List, Dict, Optional
import ssl

from loguru import logger
from dotenv import load_dotenv

try:
    from folder_learning_analyzer import FolderLearningAnalyzer, EmailFeatures
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from folder_learning_analyzer import FolderLearningAnalyzer, EmailFeatures

load_dotenv()

# Configuration
PROTON_BRIDGE_HOST = os.getenv("PROTON_BRIDGE_HOST", "127.0.0.1")
PROTON_BRIDGE_PORT = int(os.getenv("PROTON_BRIDGE_PORT", 1143))
PROTON_USERNAME = os.getenv("PROTON_USERNAME")
PROTON_PASSWORD = os.getenv("PROTON_PASSWORD")

# v1.3.0 Settings
LEARNING_ENABLED = os.getenv("PROTON_LUMO_LEARNING_ENABLED", "true").lower() == "true"
LEARNING_EMAILS_PER_FOLDER = int(os.getenv("PROTON_LUMO_LEARNING_EMAILS_PER_FOLDER", 10))
LEARNING_MIN_CONFIDENCE = float(os.getenv("PROTON_LUMO_LEARNING_MIN_CONFIDENCE", 0.7))


class SyncAndLearn:
    """
    Synchronise les dossiers ProtonMail et apprend les patterns de classification
    """
    
    def __init__(self):
        self.mailbox: Optional[imaplib.IMAP4] = None
        self.analyzer = FolderLearningAnalyzer()
        self.learning_enabled = LEARNING_ENABLED
        
        logger.info(
            f"🧠 SyncAndLearn initialized "
            f"(learning: {self.learning_enabled}, emails/folder: {LEARNING_EMAILS_PER_FOLDER})"
        )
    
    def connect(self) -> bool:
        """
        Connecte à ProtonMail Bridge
        """
        try:
            if not PROTON_USERNAME or not PROTON_PASSWORD:
                logger.error("Missing credentials in .env")
                return False
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            logger.debug(f"Connecting to {PROTON_BRIDGE_HOST}:{PROTON_BRIDGE_PORT}...")
            self.mailbox = imaplib.IMAP4(PROTON_BRIDGE_HOST, PROTON_BRIDGE_PORT, timeout=10)
            self.mailbox.starttls(ssl_context=ssl_context)
            self.mailbox.login(PROTON_USERNAME, PROTON_PASSWORD)
            
            logger.success("✓ Connected to ProtonMail Bridge")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def close(self):
        """Ferme la connexion"""
        if self.mailbox:
            try:
                self.mailbox.close()
                self.mailbox.logout()
            except:
                pass
    
    def fetch_folder_emails(self, folder_name: str, limit: int = 10) -> List[Dict]:
        """
        Récupère les derniers N emails d'un dossier
        
        Args:
            folder_name: Nom du dossier à lire
            limit: Nombre d'emails à récupérer
        
        Returns:
            Liste de dicts avec email data
        """
        emails_data = []
        
        try:
            # Sélectionner le dossier
            status, messages = self.mailbox.select(f'"{folder_name}"')
            if status != 'OK':
                logger.warning(f"Could not select folder: {folder_name}")
                return []
            
            # Récupérer tous les IDs
            status, msg_ids = self.mailbox.search(None, 'ALL')
            if status != 'OK' or not msg_ids[0]:
                logger.debug(f"No emails in {folder_name}")
                return []
            
            # Prendre les derniers N
            email_ids = msg_ids[0].split()[-limit:]  # Last N
            
            logger.info(f"Fetching {len(email_ids)} emails from {folder_name}")
            
            for email_id in email_ids:
                try:
                    status, msg_data = self.mailbox.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Extraire subject
                    subject = msg.get('Subject', 'Unknown')
                    if isinstance(subject, bytes):
                        subject = subject.decode('utf-8', errors='ignore')
                    elif isinstance(subject, email.header.Header):
                        decoded = email.header.decode_header(subject)
                        subject = decoded[0][0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(decoded[0][1] or 'utf-8', errors='ignore')
                    
                    # Extraire sender
                    sender = msg.get('From', 'Unknown')
                    if '<' in sender:
                        sender = sender.split('<')[1].split('>')[0]
                    
                    # Extraire body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                break
                    else:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    
                    # Vérifier attachments
                    has_attachment = False
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get("Content-Disposition") == "attachment":
                                has_attachment = True
                                break
                    
                    emails_data.append({
                        'subject': subject,
                        'sender': sender,
                        'body': body,
                        'has_attachment': has_attachment
                    })
                
                except Exception as e:
                    logger.debug(f"Error processing email: {e}")
                    continue
            
            logger.info(f"✓ Fetched {len(emails_data)} emails from {folder_name}")
            return emails_data
        
        except Exception as e:
            logger.error(f"Error fetching folder {folder_name}: {e}")
            return []
    
    def learn_from_folders(self, folder_mapping: Optional[Dict[str, str]] = None):
        """
        Apprend des patterns à partir des dossiers ProtonMail
        
        Args:
            folder_mapping: Dict {"Folder/Path": "CATEGORY"} (optionnel)
        """
        if not self.learning_enabled:
            logger.info("🧠 Learning disabled (PROTON_LUMO_LEARNING_ENABLED=false)")
            return
        
        logger.info("🧠 Starting folder learning analysis...")
        
        try:
            # Récupérer liste des dossiers
            status, folders = self.mailbox.list()
            if status != 'OK':
                logger.error("Could not list folders")
                return
            
            # Parser les noms de dossiers
            folder_names = []
            for folder_bytes in folders:
                try:
                    folder_raw = folder_bytes.decode('utf-8', errors='ignore')
                    parts = folder_raw.split('"')
                    if len(parts) >= 3:
                        folder_name = parts[-2]
                        # Filtrer dossiers systèmes
                        if not any(x in folder_name.lower() for x in ['[imap]', 'drafts', 'sent', 'all mail']):
                            folder_names.append(folder_name)
                except Exception as e:
                    logger.debug(f"Error parsing folder: {e}")
                    continue
            
            logger.info(f"Found {len(folder_names)} folders to analyze")
            
            # Analyser chaque dossier
            for folder_name in folder_names:
                try:
                    # Récupérer emails
                    emails_data = self.fetch_folder_emails(folder_name, LEARNING_EMAILS_PER_FOLDER)
                    
                    if not emails_data:
                        logger.debug(f"Skipping {folder_name} - no emails")
                        continue
                    
                    # Détecter la catégorie
                    category = 'UNKNOWN'
                    if folder_mapping and folder_name in folder_mapping:
                        category = folder_mapping[folder_name]
                    else:
                        # Déduire de la structure du dossier
                        category = self._infer_category(folder_name)
                    
                    # Analyser le dossier
                    pattern = self.analyzer.analyze_folder(
                        folder_name,
                        emails_data,
                        expected_category=category
                    )
                    
                    if pattern and pattern.confidence >= LEARNING_MIN_CONFIDENCE:
                        logger.success(
                            f"🧠 Learned from {folder_name}: {len(pattern.common_keywords)} keywords, "
                            f"{len(pattern.common_senders)} senders, confidence: {pattern.confidence:.0%}"
                        )
                    
                except Exception as e:
                    logger.error(f"Error analyzing folder {folder_name}: {e}")
                    continue
            
            # Sauvegarder patterns
            self.analyzer.save_patterns()
            
            # Générer rapport
            report = self.analyzer.generate_report()
            logger.info(f"\n{report}")
            
            logger.success("✓ Learning analysis complete!")
        
        except Exception as e:
            logger.error(f"Error in learning: {e}")
    
    def _infer_category(self, folder_name: str) -> str:
        """
        Déduit la catégorie du nom du dossier
        """
        folder_lower = folder_name.lower()
        
        # Mapping par mots-clés
        mappings = {
            'travail': 'PRO',
            'work': 'PRO',
            'professionnel': 'PRO',
            'banque': 'BANQUE',
            'bank': 'BANQUE',
            'finance': 'BANQUE',
            'achats': 'VENTE',
            'shopping': 'VENTE',
            'newsletter': 'NEWSLETTER',
            'social': 'SOCIAL',
            'réseaux': 'SOCIAL',
            'voyage': 'VOYAGES',
            'travel': 'VOYAGES',
            'urgent': 'URGENT',
            'traiter': 'URGENT',
        }
        
        for keyword, category in mappings.items():
            if keyword in folder_lower:
                return category
        
        return 'UNKNOWN'


def main():
    """
    Main entry point
    """
    sync_learn = SyncAndLearn()
    
    try:
        # Connecter
        if not sync_learn.connect():
            sys.exit(1)
        
        # Apprendre
        sync_learn.learn_from_folders()
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    
    finally:
        sync_learn.close()
        logger.info("Disconnected")


if __name__ == "__main__":
    main()
