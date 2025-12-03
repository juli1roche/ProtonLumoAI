#!/usr/bin/env fish
# Charge les variables d'environnement depuis le fichier .env

set -l ENV_FILE (dirname (status filename))/../.env

if test -f $ENV_FILE
    while read -l line
        if string match -q "#*" $line
            continue
        end
        if string match -q "" $line
            continue
        end
        
        set -l key (string split "=" $line)[1]
        set -l value (string split "=" $line)[2]
        
        if test -n "$key" -a -n "$value"
            set -gx $key $value
        end
    end < $ENV_FILE
    
    echo "✓ Variables d'environnement chargées"
else
    echo "✗ Fichier .env non trouvé"
end
