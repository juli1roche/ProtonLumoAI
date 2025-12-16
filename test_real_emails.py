#!/usr/bin/env python3
import sys
sys.path.append('scripts')
from email_processor import EmailProcessor
import os
from dotenv import load_dotenv

load_dotenv()

print("🚀 Test avec vrais emails (lecture seule)...")
print("⚠️  Aucun email ne sera déplacé (test uniquement)\n")

try:
    processor = EmailProcessor()

    # Afficher les métriques initiales
    print(f"📊 État initial:")
    print(f"  - Cache: {len(processor.classifier.cache)} entrées")
    print(f"  - Checkpoint: Emails déjà traités (checkpoint actif)")


    print(f"\n🔍 Prêt à traiter de nouveaux emails...")
    print(f"Appuyez sur Ctrl+C pour arrêter\n")

    # On ne lance pas run() pour l'instant, juste pour vérifier
    print("✅ Tout est prêt ! Pour lancer vraiment:")
    print("   fish run.fish")

except Exception as e:
    print(f"✗ Erreur: {e}")
    import traceback
    traceback.print_exc()
