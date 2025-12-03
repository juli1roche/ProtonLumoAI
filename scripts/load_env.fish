#!/usr/bin/env fish
# ============================================================================
# LOAD ENV - ProtonLumoAI
# Charge les variables d'environnement depuis le fichier .env
# ============================================================================

set -l ENV_FILE (dirname (status filename))/../.env

if test -f $ENV_FILE
    while read -l line
        # Ignorer les lignes vides et les commentaires
        if string match -q '#*' $line
            continue
        end
        if string match -q '' $line
            continue
        end
        
        # Extraire la clé et la valeur
        set -l key (string split '=' $line)[1]
        set -l value (string split '=' $line)[2]
        
        # Exporter la variable
        if test -n "$key" -a -n "$value"
            set -gx $key $value
        end
    end < $ENV_FILE
    
    echo "✓ Variables d'environnement chargées depuis $ENV_FILE"
else
    echo "✗ Fichier .env non trouvé: $ENV_FILE"
end
