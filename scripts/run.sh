#!/usr/bin/env bash
# Lancement de ProtonLumoAI

# Détection automatique du chemin (Correction)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Vérifier que le venv existe, sinon le créer
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "🛠️  Environnement virtuel non trouvé. Création en cours..."
    python3 -m venv "$PROJECT_ROOT/venv"
    if [ $? -ne 0 ]; then
        echo "❌ Erreur: Impossible de créer l'environnement virtuel."
        exit 1
    fi
fi

# Utilisation du chemin relatif
source "$PROJECT_ROOT/venv/bin/activate"

# Installer les dépendances
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo "📦 Installation des dépendances..."
    pip install -r "$PROJECT_ROOT/requirements.txt"
else
    echo "⚠️  Fichier requirements.txt non trouvé. L'installation des dépendances est ignorée."
fi

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
