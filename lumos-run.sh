#!/bin/bash
set -e
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
log_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
run_diagnostic() {
log_info "🔍 DIAGNOSTIC COMPLET"
python --version
[ -f .env ] && log_success "✓ .env exists" || log_warning "✗ .env missing"
[ -f email_processor.py ] && log_success "✓ email_processor.py" || log_warning "✗ missing"
[ -f scripts/pretri_folders_2025_and_gmail_fixed.py ] && log_success "✓ pretri_fixed.py" || log_warning "✗ missing"
log_success "Diagnostic complete!"
}
run_pretri() {
log_info "📧 PRÉ-TRI AUTOMATIQUE"
python scripts/pretri_folders_2025_and_gmail_fixed.py --batch-size 10 --verbose
log_success "Pretri complete!"
}
run_sync() {
log_info "🧠 APPRENTISSAGE & SYNC"
python scripts/sync_and_learn.py --learning-rate 0.8
log_success "Sync complete!"
}
run_start() {
log_info "🚀 DÉMARRAGE SERVICE"
python scripts/email_processor.py --parallel-workers 5 --batch-size 10
}
run_all() {
run_diagnostic && echo "" && run_pretri && echo "" && run_sync && echo "" && run_start
}
case "${1:-all}" in
pretri) run_pretri ;;
sync) run_sync ;;
start) run_start ;;
diagnostic) run_diagnostic ;;
all) run_all ;;
*) echo "Usage: $0 [pretri|sync|start|diagnostic|all]"; exit 1 ;;
esac
