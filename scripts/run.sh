#!/usr/bin/env bash
# Lancement de ProtonLumoAI

source "/home/johndoe/ProtonLumoAI/venv/bin/activate"
export PYTHONUNBUFFERED=1

# Charger les variables d'environnement
if [ -f "/home/johndoe/ProtonLumoAI/.env" ]; then
    export $(cat "/home/johndoe/ProtonLumoAI/.env" | grep -v '^#' | xargs)
fi

# Vérifier ProtonMail Bridge
if ! systemctl --user is-active --quiet protonmail-bridge.service; then
    echo "Démarrage de ProtonMail Bridge..."
    systemctl --user start protonmail-bridge.service
    sleep 2
fi

# Lancer le processeur
python3 "/home/johndoe/ProtonLumoAI/scripts/email_processor.py"
