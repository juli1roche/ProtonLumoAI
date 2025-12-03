#!/usr/bin/env fish
# ============================================================================
# CHECK DEPENDENCIES - ProtonLumoAI
# Vérification robuste de toutes les dépendances sur CachyOS avec Fish shell
# ============================================================================

set -l SCRIPT_DIR (dirname (status filename))
set -l PROJECT_ROOT (dirname $SCRIPT_DIR)
set -l CONFIG_FILE "$PROJECT_ROOT/config/env.fish"
set -l LOG_FILE "$PROJECT_ROOT/logs/dependency_check.log"

# --- COULEURS ---
set -l GREEN '\033[0;32m'
set -l RED '\033[0;31m'
set -l BLUE '\033[0;34m'
set -l YELLOW '\033[1;33m'
set -l NC '\033[0m'

# --- FONCTIONS DE LOG ---
function log_success
    echo -e "$GREEN[✓]$NC $argv" | tee -a $LOG_FILE
end

function log_error
    echo -e "$RED[✗]$NC $argv" >&2 | tee -a $LOG_FILE
end

function log_info
    echo -e "$BLUE[i]$NC $argv" | tee -a $LOG_FILE
end

function log_warn
    echo -e "$YELLOW[!]$NC $argv" | tee -a $LOG_FILE
end

# --- VÉRIFICATION DE BASE ---
log_info "Démarrage de la vérification des dépendances..."
log_info "Système : (uname -s) | Arch détecté"

# Vérifier que nous sommes sur Arch/CachyOS
if not string match -q "*Linux*" (uname -s)
    log_error "Ce script ne fonctionne que sur Linux"
    exit 1
end

if not command -v pacman &>/dev/null
    log_error "Pacman non trouvé. Ce script nécessite Arch/CachyOS"
    exit 1
end

log_success "Environnement CachyOS détecté"

# --- 1. VÉRIFIER FISH SHELL ---
log_info "Vérification de Fish shell..."
if not command -v fish &>/dev/null
    log_error "Fish shell non installé"
    exit 1
end
set -l FISH_VERSION (fish --version | string split ' ')
log_success "Fish shell installé : $FISH_VERSION"

# --- 2. VÉRIFIER PYTHON ---
log_info "Vérification de Python..."
if not command -v python3 &>/dev/null
    log_error "Python3 non installé"
    exit 1
end
set -l PYTHON_VERSION (python3 --version | string split ' ')
log_success "Python installé : $PYTHON_VERSION"

# Vérifier pip
if not command -v pip3 &>/dev/null
    log_warn "pip3 non trouvé, tentative d'installation..."
    sudo pacman -S --needed --noconfirm python-pip
end
log_success "pip3 disponible"

# --- 3. VÉRIFIER PROTONBRIDGE ---
log_info "Vérification de ProtonMail Bridge..."

# Option A : Vérifier si le service systemd est actif
if systemctl --user is-active --quiet protonmail-bridge.service 2>/dev/null
    log_success "ProtonMail Bridge service est actif"
    set -l BRIDGE_STATUS "active"
else
    # Option B : Vérifier si le binaire existe
    if command -v proton-bridge &>/dev/null
        log_warn "ProtonMail Bridge binaire trouvé mais service inactif"
        log_info "Tentative de démarrage du service..."
        systemctl --user enable --now protonmail-bridge.service 2>/dev/null
        sleep 2
        if systemctl --user is-active --quiet protonmail-bridge.service
            log_success "ProtonMail Bridge service démarré avec succès"
        else
            log_warn "Impossible de démarrer le service ProtonMail Bridge"
        end
    else
        log_error "ProtonMail Bridge non installé"
        log_info "Installation recommandée :"
        log_info "  Option 1 (Binaire) : paru -S proton-mail-bridge-bin"
        log_info "  Option 2 (Source)  : paru -S proton-mail-bridge"
        log_info "  Option 3 (Manuel)  : https://proton.me/mail/bridge"
        exit 1
    end
end

# Vérifier la connexion au bridge (port 1143)
log_info "Vérification de la connexion au bridge IMAP (localhost:1143)..."
if timeout 2 bash -c "echo > /dev/tcp/127.0.0.1/1143" 2>/dev/null
    log_success "ProtonMail Bridge IMAP accessible sur 127.0.0.1:1143"
else
    log_warn "ProtonMail Bridge IMAP non accessible sur 127.0.0.1:1143"
    log_info "Assurez-vous que ProtonMail Bridge est configuré et en cours d'exécution"
end

# --- 4. VÉRIFIER LUMO CLI ---
log_info "Vérification de Lumo CLI..."
if command -v lumo &>/dev/null
    set -l LUMO_VERSION (lumo --version 2>/dev/null || echo "version inconnue")
    log_success "Lumo CLI installé : $LUMO_VERSION"
else
    log_warn "Lumo CLI non installé"
    log_info "Installation recommandée :"
    log_info "  paru -S lumo-cli (si disponible)"
    log_info "  ou installation manuelle depuis https://github.com/lumo-ai/cli"
    
    # Vérifier si lumo est accessible via npm
    if command -v npm &>/dev/null
        log_info "npm détecté, tentative d'installation via npm..."
        npm install -g @lumo/cli 2>/dev/null || log_warn "Installation npm échouée"
    end
end

# --- 5. VÉRIFIER DÉPENDANCES PYTHON ---
log_info "Vérification des dépendances Python..."

set -l PYTHON_DEPS (
    "imap-tools"
    "loguru"
    "pydantic"
    "pyyaml"
    "requests"
    "scikit-learn"
    "numpy"
    "pandas"
)

set -l MISSING_DEPS
for dep in $PYTHON_DEPS
    if python3 -c "import $(string replace '-' '_' $dep)" 2>/dev/null
        log_success "  ✓ $dep"
    else
        log_warn "  ✗ $dep (manquant)"
        set -a MISSING_DEPS $dep
    end
end

if test -n "$MISSING_DEPS"
    log_info "Installation des dépendances manquantes..."
    pip3 install --upgrade $MISSING_DEPS
end

# --- 6. VÉRIFIER OUTILS SYSTÈME ---
log_info "Vérification des outils système..."

set -l SYSTEM_TOOLS (
    "git"
    "jq"
    "curl"
    "wget"
)

for tool in $SYSTEM_TOOLS
    if command -v $tool &>/dev/null
        log_success "  ✓ $tool"
    else
        log_warn "  ✗ $tool (manquant)"
        sudo pacman -S --needed --noconfirm $tool
    end
end

# --- 7. VÉRIFIER CONFIGURATION FISH ---
log_info "Vérification de la configuration Fish..."
set -l FISH_CONFIG_DIR "$HOME/.config/fish"
if test -d "$FISH_CONFIG_DIR"
    log_success "Répertoire config Fish trouvé"
else
    log_warn "Création du répertoire config Fish..."
    mkdir -p "$FISH_CONFIG_DIR/conf.d"
end

# --- 8. CRÉER FICHIER DE CONFIGURATION ENV ---
log_info "Génération du fichier de configuration d'environnement..."

cat > $CONFIG_FILE << 'EOF'
#!/usr/bin/env fish
# ProtonLumoAI - Configuration d'environnement

# Chemins
set -gx PROTON_LUMO_HOME (dirname (dirname (status filename)))
set -gx PROTON_LUMO_SCRIPTS "$PROTON_LUMO_HOME/scripts"
set -gx PROTON_LUMO_CONFIG "$PROTON_LUMO_HOME/config"
set -gx PROTON_LUMO_DATA "$PROTON_LUMO_HOME/data"
set -gx PROTON_LUMO_LOGS "$PROTON_LUMO_HOME/logs"

# ProtonMail Bridge
set -gx PROTON_BRIDGE_HOST "127.0.0.1"
set -gx PROTON_BRIDGE_PORT "1143"
set -gx PROTON_BRIDGE_SMTP_PORT "1025"

# Configuration
set -gx PROTON_LUMO_CONFIG_FILE "$PROTON_LUMO_CONFIG/config.yaml"
set -gx PROTON_LUMO_MODELS_DIR "$PROTON_LUMO_DATA/models"
set -gx PROTON_LUMO_TRAINING_DIR "$PROTON_LUMO_DATA/training"

# Logging
set -gx PROTON_LUMO_LOG_LEVEL "INFO"
set -gx PROTON_LUMO_LOG_FILE "$PROTON_LUMO_LOGS/processor.log"

# Alias utiles
alias lumo-logs="tail -f $PROTON_LUMO_LOGS/processor.log"
alias lumo-run="python3 $PROTON_LUMO_SCRIPTS/email_processor.py"
alias lumo-train="python3 $PROTON_LUMO_SCRIPTS/train_classifier.py"
alias lumo-status="systemctl --user status protonmail-bridge.service"
alias lumo-check="fish $PROTON_LUMO_SCRIPTS/check_dependencies.sh"
EOF

log_success "Configuration d'environnement créée : $CONFIG_FILE"

# --- 9. RÉSUMÉ FINAL ---
echo ""
echo -e "$BLUE========================================$NC"
echo -e "$BLUE  RÉSUMÉ DE LA VÉRIFICATION$NC"
echo -e "$BLUE========================================$NC"

set -l STATUS_OK 0
set -l STATUS_WARN 0

# Vérifications finales
if command -v python3 &>/dev/null
    echo -e "$GREEN✓$NC Python3 : OK"
else
    echo -e "$RED✗$NC Python3 : MANQUANT"
    set STATUS_OK 1
end

if command -v fish &>/dev/null
    echo -e "$GREEN✓$NC Fish shell : OK"
else
    echo -e "$RED✗$NC Fish shell : MANQUANT"
    set STATUS_OK 1
end

if command -v lumo &>/dev/null
    echo -e "$GREEN✓$NC Lumo CLI : OK"
else
    echo -e "$YELLOW!$NC Lumo CLI : À installer"
    set STATUS_WARN 1
end

if systemctl --user is-active --quiet protonmail-bridge.service 2>/dev/null
    echo -e "$GREEN✓$NC ProtonMail Bridge : OK"
else
    echo -e "$YELLOW!$NC ProtonMail Bridge : À configurer"
    set STATUS_WARN 1
end

echo ""
if test $STATUS_OK -eq 0
    if test $STATUS_WARN -eq 0
        log_success "Toutes les dépendances sont OK ! ✨"
        exit 0
    else
        log_warn "Dépendances principales OK, mais certains outils optionnels manquent"
        exit 0
    end
else
    log_error "Des dépendances critiques manquent"
    exit 1
end
