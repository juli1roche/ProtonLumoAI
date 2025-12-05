#!/usr/bin/env bash
# Lancement de ProtonLumoAI

# Détection automatique du chemin (Correction)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Utilisation du chemin relatif
source "$PROJECT_ROOT/venv/bin/activate"
export PYTHONUNBUFFERED=1

# Charger les variables d'environnement
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
fi

# Vérifier ProtonMail Bridge
if ! systemctl --user is-active --quiet protonmail-bridge.service; then
    echo "Démarrage de ProtonMail Bridge..."
    systemctl --user start protonmail-bridge.service
    sleep 2
fi

# Lancer le processeur
python3 "$SCRIPT_DIR/email_processor.py"
