#!/usr/bin/env fish
# Script de démarrage pour ProtonLumoAI avec Fish shell
# Utilisation: fish run.fish

# Obtenir le répertoire du script
set -l SCRIPT_DIR (dirname (status filename))
cd $SCRIPT_DIR

# Désactiver tout venv actif (Fish shell)
if set -q VIRTUAL_ENV
    echo "⚠️  Désactivation du venv actif..."
    if functions -q deactivate
        deactivate nondestructive
    else
        set -e VIRTUAL_ENV
        set -e VIRTUAL_ENV_PROMPT
    end
end

# Vérifier que le venv existe, sinon le créer
if not test -d "venv"
    echo "🛠️  Environnement virtuel non trouvé. Création en cours..."
    python3 -m venv venv
    if test $status -ne 0
        echo "❌ Erreur: Impossible de créer l'environnement virtuel."
        exit 1
    end
end

# Activer l'environnement virtuel
source venv/bin/activate.fish

# Définir le chemin vers l'exécutable Python du venv
set -l PYTHON_BIN (pwd)/venv/bin/python3

# Installer les dépendances
if test -f "requirements.txt"
    echo "📦 Installation des dépendances..."
    $PYTHON_BIN -m pip install -r requirements.txt
else
    echo "⚠️  Fichier requirements.txt non trouvé. L'installation des dépendances est ignorée."
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

# Synchroniser les dossiers avant de démarrer
echo "🔄 Synchronisation des dossiers ProtonMail..."
$PYTHON_BIN scripts/sync_folders.py

echo "🚀 Démarrage du processeur d'emails..."
echo ""

# Exécuter avec le Python du venv
$PYTHON_BIN scripts/email_processor.py
