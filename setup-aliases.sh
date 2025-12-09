#!/usr/bin/env bash
# ============================================================================
# Configuration des alias Fish pour ProtonLumoAI
# ============================================================================

set -e

PROJECT_ROOT="$(pwd)"
FISH_CONFIG="$HOME/.config/fish/config.fish"
ALIAS_FILE="$PROJECT_ROOT/config/fish_aliases.fish"

echo "🐟 Configuration des alias Fish pour ProtonLumoAI..."
echo ""

# Vérifier si Fish est installé
if ! command -v fish &> /dev/null; then
    echo "⚠️  Fish shell n'est pas installé."
    echo "   Installez Fish : sudo pacman -S fish"
    exit 1
fi

# Créer le répertoire de config Fish si nécessaire
mkdir -p "$(dirname "$FISH_CONFIG")"

# Vérifier si les alias sont déjà configurés
if grep -q "ProtonLumoAI" "$FISH_CONFIG" 2>/dev/null; then
    echo "ℹ️  Les alias sont déjà configurés dans $FISH_CONFIG"
    echo "   Si vous voulez les reconfigurer, supprimez la ligne et relancez ce script."
    exit 0
fi

# Ajouter le source des alias au config Fish
echo "" >> "$FISH_CONFIG"
echo "# ProtonLumoAI Aliases" >> "$FISH_CONFIG"
echo "source $ALIAS_FILE" >> "$FISH_CONFIG"

echo "✅ Alias configurés dans $FISH_CONFIG"
echo ""
echo "Pour activer les alias dans votre session actuelle :"
echo "  source $FISH_CONFIG"
echo ""
echo "Ou redémarrez votre terminal."
echo ""
echo "Tapez 'lumo-help' pour voir toutes les commandes disponibles."
echo ""
EOF
