#!/usr/bin/env fish
# Script de démarrage pour ProtonLumoAI avec Fish shell
# Utilisation: fish run.fish

# Obtenir le répertoire du script
set -l SCRIPT_DIR (dirname (status filename))
cd $SCRIPT_DIR

# Vérifier que le venv existe
if not test -d "venv"
    echo "❌ Erreur: Environnement virtuel non trouvé"
    echo "Créez-le avec: python3 -m venv venv"
    exit 1
end

# Vérifier que .env existe
if not test -f ".env"
    echo "❌ Erreur: Fichier .env non trouvé"
    echo "Créez-le en copiant .env.example:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
end

# Charger les variables d'environnement depuis .env
echo "📝 Chargement des variables d'environnement..."
set -l ENV_FILE ".env"
for line in (grep -v '^#' $ENV_FILE | grep -v '^$')
    set -l key (echo $line | cut -d '=' -f 1)
    set -l value (echo $line | cut -d '=' -f 2-)
    set -gx $key $value
end

# Vérifier les variables essentielles
if test -z "$PROTON_USERNAME" -o -z "$PROTON_PASSWORD"
    echo "❌ Erreur: PROTON_USERNAME et PROTON_PASSWORD doivent être définis dans .env"
    exit 1
end

echo "✓ Configuration chargée"
echo "  - Host: $PROTON_BRIDGE_HOST:$PROTON_BRIDGE_PORT"
echo "  - Username: $PROTON_USERNAME"
echo ""
echo "🚀 Démarrage du processeur d'emails..."
echo ""

# Lancer le processeur avec le Python du venv
# Cela évite les problèmes d'activation du venv dans Fish shell
set -l PYTHON_BIN "./venv/bin/python3"

if not test -f $PYTHON_BIN
    echo "❌ Erreur: Python du venv non trouvé à $PYTHON_BIN"
    exit 1
end

# Exécuter avec le Python du venv
$PYTHON_BIN scripts/email_processor.py
