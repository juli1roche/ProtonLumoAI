#!/usr/bin/env bash
# ============================================================================
# Désinstallation du service systemd ProtonLumoAI
# ============================================================================

set -e

USER_SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "🗑️  Désinstallation du service systemd ProtonLumoAI..."
echo ""

# Arrêter le service s'il tourne
if systemctl --user is-active --quiet protonlumoai.service; then
    echo "⏹️  Arrêt du service..."
    systemctl --user stop protonlumoai.service
fi

# Désactiver le service
if systemctl --user is-enabled --quiet protonlumoai.service; then
    echo "❌ Désactivation du service..."
    systemctl --user disable protonlumoai.service
fi

# Supprimer le fichier de service
if [ -f "$USER_SYSTEMD_DIR/protonlumoai.service" ]; then
    echo "🗑️  Suppression du fichier de service..."
    rm "$USER_SYSTEMD_DIR/protonlumoai.service"
fi

# Recharger systemd
echo "🔄 Rechargement de systemd..."
systemctl --user daemon-reload

echo ""
echo "✅ Désinstallation terminée !"
echo ""
echo "Note: Le linger est toujours activé. Pour le désactiver :"
echo "  sudo loginctl disable-linger $USER"
echo ""