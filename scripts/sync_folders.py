#!/usr/bin/env python3
# ============================================================================
# SYNC FOLDERS - ProtonLumoAI v2.1
# Adapté pour la nouvelle classe ProtonMailBox
# ============================================================================

import os
import json
import sys
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

try:
    from email_processor import ProtonMailBox
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from email_processor import ProtonMailBox

load_dotenv()

CONFIG_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / "../config/categories.json"

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
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.success(f"Configuration sauvegardée dans {CONFIG_PATH}")

def sanitize_category_name(folder_name):
    return folder_name.upper().replace('/', '_').replace(' ', '_').replace('-', '_')

def sync():
    logger.info("Démarrage de la synchronisation des dossiers...")
    current_config = load_config()
    existing_paths = {cat['folder']: key for key, cat in current_config.items()}

    try:
        # CORRECTION ICI : Appel sans arguments (la classe lit le .env)
        with ProtonMailBox() as mailbox:
            status, folders = mailbox.client.list()

            if status != 'OK':
                logger.error("Impossible de lister les dossiers")
                return

            new_folders_count = 0

            for folder_bytes in folders:
                folder_raw = folder_bytes.decode()
                folder_name = folder_raw.split(' "/" ')[-1].strip('"')

                if (folder_name in EXCLUDED_FOLDERS or
                    folder_name.startswith("Training") or
                    folder_name.startswith("Feedback") or
                    folder_name.startswith("Corrections")):
                    continue

                if folder_name in existing_paths:
                    logger.debug(f"✓ Dossier connu : {folder_name}")
                else:
                    cat_key = sanitize_category_name(folder_name)
                    if cat_key in current_config:
                        cat_key = f"{cat_key}_AUTO"

                    logger.info(f"+ Ajout nouvelle catégorie : {cat_key} -> {folder_name}")

                    current_config[cat_key] = {
                        "name": cat_key,
                        "folder": folder_name,
                        "keywords": [],
                        "confidence_threshold": 0.7,
                        "priority": 2,
                        "description": f"Dossier auto-détecté : {folder_name}"
                    }
                    new_folders_count += 1

            if new_folders_count > 0:
                save_config(current_config)
                logger.success(f"Synchronisation terminée : {new_folders_count} nouvelles catégories.")
            else:
                logger.info("Synchronisation terminée : Aucune modification nécessaire.")

    except Exception as e:
        logger.error(f"Erreur de synchronisation : {e}")

if __name__ == "__main__":
    sync()
