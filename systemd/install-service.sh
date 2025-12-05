#!/usr/bin/env bash
# ============================================================================
# Installation du service systemd ProtonLumoAI
# ============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$SCRIPT_DIR/protonlumoai.service"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "🚀 Installation du service systemd ProtonLumoAI..."
echo ""

# Vérifier que le fichier .env existe
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "❌ Erreur: Le fichier .env n'existe pas."
    echo "   Créez d'abord le fichier .env avec vos identifiants."
    echo "   Voir README.md pour les instructions."
    exit 1
fi

# Vérifier que l'environnement virtuel existe
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "⚠️  L'environnement virtuel n'existe pas. Création..."
    cd "$PROJECT_ROOT"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    echo "✓ Environnement virtuel créé"
fi

# Créer le répertoire systemd utilisateur
mkdir -p "$USER_SYSTEMD_DIR"

# Remplacer %h par le chemin réel du home
HOME_PATH="$HOME"
TEMP_SERVICE="/tmp/protonlumoai.service"
sed "s|%h|$HOME_PATH|g" "$SERVICE_FILE" > "$TEMP_SERVICE"
sed -i "s|%u|$USER|g" "$TEMP_SERVICE"

# Copier le fichier de service
echo "📝 Copie du fichier de service..."
cp "$TEMP_SERVICE" "$USER_SYSTEMD_DIR/protonlumoai.service"
rm "$TEMP_SERVICE"

# Recharger systemd
echo "🔄 Rechargement de systemd..."
systemctl --user daemon-reload

# Activer le service au démarrage
echo "✅ Activation du service au démarrage..."
systemctl --user enable protonlumoai.service

# Activer linger pour que le service démarre sans login
echo "🔐 Activation du linger (démarrage sans login)..."
sudo loginctl enable-linger "$USER"

echo ""
echo "✅ Installation terminée !"
echo ""
echo "Commandes disponibles :"
echo "  systemctl --user start protonlumoai     # Démarrer maintenant"
echo "  systemctl --user stop protonlumoai      # Arrêter"
echo "  systemctl --user restart protonlumoai   # Redémarrer"
echo "  systemctl --user status protonlumoai    # Voir le statut"
echo "  journalctl --user -u protonlumoai -f    # Voir les logs en temps réel"
echo "  systemctl --user disable protonlumoai   # Désactiver au démarrage"
echo ""
echo "🚀 Le service démarrera automatiquement au prochain redémarrage."
echo ""