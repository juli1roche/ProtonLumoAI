#!/usr/bin/env bash
# ============================================================================
# SETUP PROTONBRIDGE - ProtonLumoAI
# Script pour configurer ProtonMail Bridge avec vos identifiants
# ============================================================================

set -e

echo "=========================================="
echo "  Configuration de ProtonMail Bridge"
echo "=========================================="
echo ""

# Vérifier que ProtonMail Bridge est installé
if ! command -v proton-bridge &> /dev/null; then
    echo "❌ ProtonMail Bridge n'est pas installé"
    echo "Installez-le avec : sudo cp ~/proton-bridge/bridge /usr/local/bin/proton-bridge"
    exit 1
fi

echo "✓ ProtonMail Bridge trouvé"
echo ""

# Lire les identifiants depuis .env
ENV_FILE="$(dirname "$0")/../.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Fichier .env non trouvé"
    exit 1
fi

# Sourcer le fichier .env
export $(cat "$ENV_FILE" | grep -v '^#' | xargs)

echo "Configuration trouvée :"
echo "  Email : $PROTON_USERNAME"
echo ""

# Créer le répertoire de configuration s'il n'existe pas
mkdir -p ~/.config/protonmail/bridge-v3

echo "⚠️  IMPORTANT :"
echo "ProtonMail Bridge doit être configuré de manière interactive."
echo "Vous devez :"
echo ""
echo "1. Ouvrir l'interface graphique de ProtonMail Bridge"
echo "2. Ajouter votre compte avec vos identifiants ProtonMail"
echo "3. Copier le mot de passe IMAP généré"
echo "4. Mettre à jour le fichier .env avec ce mot de passe IMAP"
echo ""
echo "Commandes :"
echo ""
echo "  # Lancer l'interface graphique (avec X11)"
echo "  flatpak run ch.protonmail.protonmail-bridge"
echo ""
echo "  # Ou lancer en mode gRPC (sans interface)"
echo "  proton-bridge --grpc --noninteractive &"
echo ""
echo "Après configuration, vérifiez la connexion :"
echo "  python3 scripts/email_processor.py"
echo ""
