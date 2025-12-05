#!/usr/bin/env python3
# ============================================================================
# SYNC FOLDERS - ProtonLumoAI
# Synchronise la structure des dossiers ProtonMail avec categories.json
# ============================================================================

import os
import json
import sys
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# Import de la classe de connexion existante
try:
    from email_processor import ProtonMailBox
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from email_processor import ProtonMailBox

# Chargement env
load_dotenv()

# Configuration
CONFIG_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / "../config/categories.json"
PROTON_BRIDGE_HOST = os.getenv("PROTON_BRIDGE_HOST", "127.0.0.1")
PROTON_BRIDGE_PORT = int(os.getenv("PROTON_BRIDGE_PORT", 1143))
PROTON_USERNAME = os.getenv("PROTON_USERNAME")
PROTON_PASSWORD = os.getenv("PROTON_PASSWORD")

# Dossiers à ignorer (Système)
EXCLUDED_FOLDERS = [
    "Trash", "Corbeille", "Bin",
    "Spam", "Junk", "Pourriel",
    "Archive", "Archives",
    "Sent", "Sent Messages", "Envoyés",
    "Drafts", "Brouillons",
    "All Mail", "Tous les messages",
    "INBOX"
]

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.success(f"Configuration sauvegardée dans {CONFIG_PATH}")

def sanitize_category_name(folder_name):
    """Transforme un nom de dossier en clé de catégorie (ex: 'Travail/Projets' -> 'TRAVAIL_PROJETS')"""
    return folder_name.upper().replace('/', '_').replace(' ', '_').replace('-', '_')

def sync():
    logger.info("Démarrage de la synchronisation des dossiers...")
    
    current_config = load_config()
    existing_paths = {cat['folder']: key for key, cat in current_config.items()}
    
    # Connexion
    try:
        with ProtonMailBox(PROTON_BRIDGE_HOST, PROTON_BRIDGE_PORT, PROTON_USERNAME, PROTON_PASSWORD) as mailbox:
            status, folders = mailbox.client.list()
            
            if status != 'OK':
                logger.error("Impossible de lister les dossiers")
                return

            new_folders_count = 0
            
            for folder_bytes in folders:
                try:
                    folder_raw = folder_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    folder_raw = folder_bytes.decode('latin-1') # Fallback

                parts = folder_raw.split(' "/" ')
                if len(parts) > 1:
                    folder_name = parts[-1].strip('"')
                else:
                    continue # Skip invalid folder format
                
                # Ignorer dossiers système et dossiers d'entraînement
                if (folder_name in EXCLUDED_FOLDERS or 
                    folder_name.startswith("Training") or 
                    folder_name.startswith("Feedback") or
                    folder_name.startswith("Corrections")):
                    continue

                logger.debug(f"Dossier trouvé : {folder_name}")

                # Vérifier si ce dossier est déjà configuré
                if folder_name in existing_paths:
                    logger.info(f"✓ Dossier connu : {folder_name} (Catégorie : {existing_paths[folder_name]})")
                else:
                    # CRÉATION D'UNE NOUVELLE CATÉGORIE
                    cat_key = sanitize_category_name(folder_name)
                    
                    # Éviter d'écraser si la clé existe déjà mais pointe ailleurs
                    if cat_key in current_config:
                        cat_key = f"{cat_key}_AUTO"

                    logger.info(f"+ Ajout nouvelle catégorie : {cat_key} -> {folder_name}")
                    
                    current_config[cat_key] = {
                        "name": cat_key,
                        "folder": folder_name,
                        "keywords": [], # Pas de mots-clés par défaut, l'IA gérera
                        "confidence_threshold": 0.7,
                        "priority": 2,
                        "description": f"Dossier auto-détecté : {folder_name}"
                    }
                    new_folders_count += 1

            if new_folders_count > 0:
                save_config(current_config)
                logger.success(f"Synchronisation terminée : {new_folders_count} nouvelles catégories ajoutées.")
            else:
                logger.info("Synchronisation terminée : Aucune modification nécessaire.")

    except Exception as e:
        logger.error(f"Erreur de synchronisation : {e}")

if __name__ == "__main__":
    sync()
