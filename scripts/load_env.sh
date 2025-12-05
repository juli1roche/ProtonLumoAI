#!/bin/bash
# Script de chargement des variables d'environnement pour ProtonLumoAI

# Obtenir le répertoire du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

# Vérifier que le fichier .env existe
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Erreur: Fichier .env non trouvé à $ENV_FILE"
    echo "Créez le fichier .env en copiant .env.example:"
    echo "  cp $PROJECT_DIR/.env.example $PROJECT_DIR/.env"
    echo "  nano $PROJECT_DIR/.env"
    return 1
fi

# Charger les variables d'environnement
set -a
source "$ENV_FILE"
set +a

# Vérifier que les variables essentielles sont définies
if [ -z "$PROTON_USERNAME" ] || [ -z "$PROTON_PASSWORD" ]; then
    echo "❌ Erreur: PROTON_USERNAME et PROTON_PASSWORD doivent être définis dans .env"
    return 1
fi

echo "✓ Variables d'environnement chargées depuis $ENV_FILE"
echo "  - Host: $PROTON_BRIDGE_HOST:$PROTON_BRIDGE_PORT"
echo "  - Username: $PROTON_USERNAME"
echo "  - Poll Interval: ${PROTON_LUMO_POLL_INTERVAL}s"

return 0
