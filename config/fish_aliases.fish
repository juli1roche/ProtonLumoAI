# ============================================================================
# ProtonLumoAI - Fish Shell Aliases
# Ajoutez ce fichier à votre config Fish ou sourcez-le
# ============================================================================

# Alias pour la gestion du service
alias lumo-start='systemctl --user start protonlumoai'
alias lumo-stop='systemctl --user stop protonlumoai'
alias lumo-restart='systemctl --user restart protonlumoai'
alias lumo-status='systemctl --user status protonlumoai'
alias lumo-enable='systemctl --user enable protonlumoai'
alias lumo-disable='systemctl --user disable protonlumoai'

# Alias pour les logs
alias lumo-logs='journalctl --user -u protonlumoai -f'
alias lumo-logs-all='journalctl --user -u protonlumoai --no-pager'
alias lumo-logs-errors='journalctl --user -u protonlumoai -p err --no-pager'
alias lumo-logs-today='journalctl --user -u protonlumoai --since today --no-pager'

# Alias pour le monitoring
alias lumo-stats='cat ~/ProtonLumoAI/data/checkpoint.json | jq .'
alias lumo-corrections='cat ~/ProtonLumoAI/data/learning/user_corrections.jsonl | jq .'
alias lumo-patterns='cat ~/ProtonLumoAI/data/learning/learned_patterns.json | jq .'

# Alias pour le mode interactif (sans service)
alias lumo-run='cd ~/ProtonLumoAI && source venv/bin/activate && python scripts/main.py'
alias lumo-dry-run='cd ~/ProtonLumoAI && export PROTON_LUMO_DRY_RUN=true && source venv/bin/activate && python scripts/main.py'

# Alias pour la maintenance
alias lumo-reset-checkpoint='rm ~/ProtonLumoAI/data/checkpoint.json && echo "Checkpoint réinitialisé"'
alias lumo-reset-learning='rm -rf ~/ProtonLumoAI/data/learning/* && echo "Données d\'apprentissage réinitialisées"'
alias lumo-backup='tar -czf ~/protonlumoai-backup-$(date +%Y%m%d-%H%M%S).tar.gz ~/ProtonLumoAI/data ~/ProtonLumoAI/config ~/ProtonLumoAI/.env'

# Fonction pour voir les statistiques
function lumo-report
    echo "📊 Statistiques ProtonLumoAI"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Statut du service
    echo ""
    echo "🔋 Service:"
    systemctl --user is-active protonlumoai && echo "  ✅ Actif" || echo "  ❌ Inactif"
    systemctl --user is-enabled protonlumoai && echo "  ✅ Démarrage auto activé" || echo "  ❌ Démarrage auto désactivé"
    
    # Checkpoint
    if test -f ~/ProtonLumoAI/data/checkpoint.json
        echo ""
        echo "💾 Checkpoint:"
        set processed (jq -r '.processed_emails | length' ~/ProtonLumoAI/data/checkpoint.json 2>/dev/null)
        set last_update (jq -r '.last_update' ~/ProtonLumoAI/data/checkpoint.json 2>/dev/null)
        echo "  Emails traités: $processed"
        echo "  Dernière mise à jour: $last_update"
    end
    
    # Apprentissage
    if test -f ~/ProtonLumoAI/data/learning/user_corrections.jsonl
        echo ""
        echo "🧠 Apprentissage:"
        set corrections (wc -l < ~/ProtonLumoAI/data/learning/user_corrections.jsonl 2>/dev/null)
        echo "  Corrections utilisateur: $corrections"
        
        if test -f ~/ProtonLumoAI/data/learning/learned_patterns.json
            set sender_rules (jq -r '.sender_rules | length' ~/ProtonLumoAI/data/learning/learned_patterns.json 2>/dev/null)
            set domain_rules (jq -r '.domain_rules | length' ~/ProtonLumoAI/data/learning/learned_patterns.json 2>/dev/null)
            set keywords (jq -r '.subject_keywords | length' ~/ProtonLumoAI/data/learning/learned_patterns.json 2>/dev/null)
            echo "  Règles expéditeur: $sender_rules"
            echo "  Règles domaine: $domain_rules"
            echo "  Mots-clés appris: $keywords"
        end
    end
    
    # Logs récents
    echo ""
    echo "📝 Dernières activités (5 dernières lignes):"
    journalctl --user -u protonlumoai -n 5 --no-pager 2>/dev/null || echo "  Aucun log disponible"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
end

# Message d'aide
function lumo-help
    echo "🤖 ProtonLumoAI - Commandes Disponibles"
    echo ""
    echo "Gestion du Service:"
    echo "  lumo-start          Démarrer le service"
    echo "  lumo-stop           Arrêter le service"
    echo "  lumo-restart        Redémarrer le service"
    echo "  lumo-status         Voir le statut du service"
    echo "  lumo-enable         Activer au démarrage"
    echo "  lumo-disable        Désactiver au démarrage"
    echo ""
    echo "Logs:"
    echo "  lumo-logs           Logs en temps réel"
    echo "  lumo-logs-all       Tous les logs"
    echo "  lumo-logs-errors    Erreurs uniquement"
    echo "  lumo-logs-today     Logs d'aujourd'hui"
    echo ""
    echo "Monitoring:"
    echo "  lumo-report         Rapport complet"
    echo "  lumo-stats          Statistiques checkpoint"
    echo "  lumo-corrections    Corrections utilisateur"
    echo "  lumo-patterns       Patterns appris"
    echo ""
    echo "Maintenance:"
    echo "  lumo-reset-checkpoint   Réinitialiser le checkpoint"
    echo "  lumo-reset-learning     Réinitialiser l'apprentissage"
    echo "  lumo-backup            Sauvegarder les données"
    echo ""
    echo "Mode Interactif:"
    echo "  lumo-run            Lancer sans service"
    echo "  lumo-dry-run        Test sans déplacement"
    echo ""
end

echo "✅ Alias ProtonLumoAI chargés. Tapez 'lumo-help' pour voir les commandes."