#!/usr/bin/env bash
# ============================================================================
# INSTALLATION - ProtonLumoAI
# Installation complète et configuration sur CachyOS
# ============================================================================

set -euo pipefail
IFS=$'\n\t'

# --- COULEURS & LOGS ---
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[+]${NC} $1"; }
info() { echo -e "${BLUE}[i]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[X]${NC} $1" >&2; }

# --- DÉTECTION RÉPERTOIRES ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/venv"
CONFIG_DIR="$PROJECT_ROOT/config"
DATA_DIR="$PROJECT_ROOT/data"
LOGS_DIR="$PROJECT_ROOT/logs"

log "Installation de ProtonLumoAI"
log "Répertoire du projet: $PROJECT_ROOT"

# --- 1. VÉRIFIER LES PRÉREQUIS SYSTÈME ---
log "Vérification des prérequis système..."

if ! command -v python3 &>/dev/null; then
    err "Python3 non installé"
    exit 1
fi
info "✓ Python3: $(python3 --version)"

if ! command -v fish &>/dev/null; then
    warn "Fish shell non installé, installation..."
    sudo pacman -S --needed --noconfirm fish
fi
info "✓ Fish: $(fish --version)"

# --- 2. CRÉER L'ENVIRONNEMENT VIRTUEL ---
log "Configuration de l'environnement Python..."

if [ ! -d "$VENV_DIR" ]; then
    log "Création de l'environnement virtuel..."
    python3 -m venv "$VENV_DIR"
else
    info "Environnement virtuel existant"
fi

# Activer le venv
source "$VENV_DIR/bin/activate"

# --- 3. INSTALLER LES DÉPENDANCES PYTHON ---
log "Installation des dépendances Python..."

pip install --upgrade pip setuptools wheel

# Dépendances principales
pip install \
    imap-tools \
    loguru \
    pydantic \
    pyyaml \
    requests \
    scikit-learn \
    numpy \
    pandas \
    python-dotenv

info "✓ Dépendances Python installées"

# --- 4. CRÉER LES RÉPERTOIRES ---
log "Création de la structure de répertoires..."

mkdir -p "$CONFIG_DIR"
mkdir -p "$DATA_DIR"/{models,training,cache}
mkdir -p "$LOGS_DIR"

info "✓ Répertoires créés"

# --- 5. CRÉER LES FICHIERS DE CONFIGURATION ---
log "Création des fichiers de configuration..."

# Fichier .env
cat > "$PROJECT_ROOT/.env" << 'EOF'
# ProtonLumoAI Configuration

# ProtonMail Bridge
PROTON_BRIDGE_HOST=127.0.0.1
PROTON_BRIDGE_PORT=1143
PROTON_BRIDGE_SMTP_PORT=1025

# Identifiants ProtonMail (à configurer)
PROTON_USERNAME=your_email@proton.me
PROTON_PASSWORD=your_bridge_password

# Configuration de traitement
PROTON_LUMO_POLL_INTERVAL=60
PROTON_LUMO_AUTO_IMPROVE_INTERVAL=3600
PROTON_LUMO_UNSEEN_ONLY=true
PROTON_LUMO_DRY_RUN=false

# Logging
PROTON_LUMO_LOG_LEVEL=INFO
EOF

info "✓ Fichier .env créé (à configurer)"

# Fichier config.yaml
cat > "$CONFIG_DIR/config.yaml" << 'EOF'
# ProtonLumoAI Configuration

bridge:
  host: 127.0.0.1
  port: 1143
  smtp_port: 1025

processing:
  poll_interval: 60  # secondes
  auto_improve_interval: 3600  # 1 heure
  process_unseen_only: true
  dry_run: false

classification:
  confidence_threshold: 0.6
  use_lumo: true
  use_keywords_fallback: true

training:
  auto_train: true
  evaluation_interval: 3600
  min_examples_for_training: 10

logging:
  level: INFO
  rotation: "10 MB"
  retention: "30 days"
EOF

info "✓ Fichier config.yaml créé"

# --- 6. CRÉER LES SCRIPTS SYSTEMD ---
log "Création des services systemd..."

# Service principal
cat > "$HOME/.config/systemd/user/proton-lumo-processor.service" << EOF
[Unit]
Description=ProtonLumoAI Email Processor
After=protonmail-bridge.service
Wants=protonmail-bridge.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$PROJECT_ROOT/.env
ExecStart=$VENV_DIR/bin/python3 $SCRIPT_DIR/email_processor.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF

# Service d'amélioration automatique (optionnel, basé sur timer)
cat > "$HOME/.config/systemd/user/proton-lumo-improve.service" << EOF
[Unit]
Description=ProtonLumoAI Auto-Improvement
After=protonmail-bridge.service

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$PROJECT_ROOT/.env
ExecStart=$VENV_DIR/bin/python3 $SCRIPT_DIR/train_classifier.py
EOF

# Timer pour l'amélioration automatique
cat > "$HOME/.config/systemd/user/proton-lumo-improve.timer" << EOF
[Unit]
Description=ProtonLumoAI Auto-Improvement Timer
Requires=proton-lumo-improve.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Recharger les services
systemctl --user daemon-reload

info "✓ Services systemd créés"

# --- 7. CONFIGURER FISH SHELL ---
log "Configuration de Fish shell..."

FISH_CONF="$HOME/.config/fish/conf.d/proton-lumo.fish"

mkdir -p "$HOME/.config/fish/conf.d"

cat > "$FISH_CONF" << 'EOF'
#!/usr/bin/env fish
# ProtonLumoAI Configuration for Fish Shell

# Déterminer le répertoire du projet
set -l PROTON_LUMO_HOME (dirname (dirname (status filename)))
if not test -d "$PROTON_LUMO_HOME/ProtonLumoAI"
    set PROTON_LUMO_HOME "$HOME/ProtonLumoAI"
end

# Variables d'environnement
set -gx PROTON_LUMO_HOME "$PROTON_LUMO_HOME"
set -gx PROTON_LUMO_SCRIPTS "$PROTON_LUMO_HOME/scripts"
set -gx PROTON_LUMO_CONFIG "$PROTON_LUMO_HOME/config"
set -gx PROTON_LUMO_DATA "$PROTON_LUMO_HOME/data"
set -gx PROTON_LUMO_LOGS "$PROTON_LUMO_HOME/logs"

# Charger les variables d'environnement du fichier .env
if test -f "$PROTON_LUMO_HOME/.env"
    set -l env_file (cat "$PROTON_LUMO_HOME/.env" | grep -v '^#' | grep '=')
    for line in $env_file
        set -l key (echo $line | cut -d'=' -f1)
        set -l value (echo $line | cut -d'=' -f2-)
        set -gx $key $value
    end
end

# Alias utiles
alias lumo-logs="tail -f $PROTON_LUMO_LOGS/processor.log"
alias lumo-run="$PROTON_LUMO_SCRIPTS/run.sh"
alias lumo-train="python3 $PROTON_LUMO_SCRIPTS/train_classifier.py"
alias lumo-check="fish $PROTON_LUMO_SCRIPTS/check_dependencies.sh"
alias lumo-status="systemctl --user status proton-lumo-processor.service"
alias lumo-start="systemctl --user start proton-lumo-processor.service"
alias lumo-stop="systemctl --user stop proton-lumo-processor.service"
alias lumo-restart="systemctl --user restart proton-lumo-processor.service"
alias lumo-enable="systemctl --user enable proton-lumo-processor.service"
alias lumo-disable="systemctl --user disable proton-lumo-processor.service"
EOF

info "✓ Configuration Fish créée"

# --- 8. CRÉER LE SCRIPT DE LANCEMENT ---
log "Création du script de lancement..."

cat > "$SCRIPT_DIR/run.sh" << EOF
#!/usr/bin/env bash
# Lancement de ProtonLumoAI

source "$VENV_DIR/bin/activate"
export PYTHONUNBUFFERED=1

# Charger les variables d'environnement
if [ -f "$PROJECT_ROOT/.env" ]; then
    export \$(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
fi

# Vérifier ProtonMail Bridge
if ! systemctl --user is-active --quiet protonmail-bridge.service; then
    echo "Démarrage de ProtonMail Bridge..."
    systemctl --user start protonmail-bridge.service
    sleep 2
fi

# Lancer le processeur
python3 "$SCRIPT_DIR/email_processor.py"
EOF

chmod +x "$SCRIPT_DIR/run.sh"
info "✓ Script de lancement créé"

# --- 9. RÉSUMÉ ET INSTRUCTIONS ---
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  INSTALLATION TERMINÉE ✓${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Prochaines étapes :"
echo ""
echo "1. Configurer les identifiants ProtonMail :"
echo "   nano $PROJECT_ROOT/.env"
echo ""
echo "2. Vérifier les dépendances :"
echo "   fish $SCRIPT_DIR/check_dependencies.sh"
echo ""
echo "3. Démarrer le service :"
echo "   systemctl --user start proton-lumo-processor.service"
echo ""
echo "4. Voir les logs :"
echo "   tail -f $LOGS_DIR/processor.log"
echo ""
echo "Alias Fish disponibles :"
echo "   lumo-start      - Démarrer le service"
echo "   lumo-stop       - Arrêter le service"
echo "   lumo-logs       - Voir les logs"
echo "   lumo-status     - Voir le statut"
echo "   lumo-check      - Vérifier les dépendances"
echo ""
echo -e "${GREEN}Installation réussie !${NC}"
