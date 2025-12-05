#!/usr/bin/env fish
# Script d'activation pour Fish shell
# Active l'environnement virtuel et charge les variables d'environnement

# Obtenir le répertoire du script
set -l SCRIPT_DIR (dirname (status filename))
set -l PROJECT_DIR (dirname $SCRIPT_DIR)

# Activer l'environnement virtuel Python
if test -f "$PROJECT_DIR/venv/bin/activate.fish"
    source "$PROJECT_DIR/venv/bin/activate.fish"
else
    echo "❌ Erreur: Environnement virtuel non trouvé à $PROJECT_DIR/venv"
    echo "Créez-le avec: python3 -m venv $PROJECT_DIR/venv"
    return 1
end

# Charger les variables d'environnement
if test -f "$PROJECT_DIR/scripts/load_env.fish"
    source "$PROJECT_DIR/scripts/load_env.fish"
else
    echo "❌ Erreur: Script load_env.fish non trouvé"
    return 1
end

echo "✓ Environnement ProtonLumoAI activé"
# Ne pas retourner, laisser le shell continuer
