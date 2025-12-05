#!/usr/bin/env python3
"""
Test de connexion IMAP à ProtonMail Bridge
"""

import ssl
import imaplib
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

IMAP_HOST = os.getenv("PROTON_BRIDGE_HOST", "127.0.0.1")
IMAP_PORT = int(os.getenv("PROTON_BRIDGE_PORT", 1143))
IMAP_USERNAME = os.getenv("PROTON_USERNAME")
IMAP_PASSWORD = os.getenv("PROTON_PASSWORD")

print(f"Configuration:")
print(f"  Host: {IMAP_HOST}")
print(f"  Port: {IMAP_PORT}")
print(f"  Username: {IMAP_USERNAME}")
print()

try:
    print("1. Création du contexte SSL...")
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    print("   ✓ Contexte SSL créé")
    
    print("2. Connexion IMAP4_SSL...")
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=ssl_context)
    print("   ✓ Connexion SSL établie")
    
    print("3. Authentification...")
    imap.login(IMAP_USERNAME, IMAP_PASSWORD)
    print("   ✓ Authentification réussie")
    
    print("4. Listage des dossiers...")
    status, mailboxes = imap.list()
    print(f"   ✓ {len(mailboxes)} dossiers trouvés")
    for mailbox in mailboxes[:5]:  # Afficher les 5 premiers
        print(f"     - {mailbox.decode()}")
    
    print("5. Sélection de INBOX...")
    status, count = imap.select("INBOX")
    print(f"   ✓ {count[0].decode()} emails dans INBOX")
    
    print("6. Déconnexion...")
    imap.logout()
    print("   ✓ Déconnexion réussie")
    
    print()
    print("✓ SUCCÈS ! Connexion IMAP fonctionnelle")
    
except Exception as e:
    print(f"✗ ERREUR: {e}")
    import traceback
    traceback.print_exc()
