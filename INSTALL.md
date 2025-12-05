# 🚀 Guide d'Installation ProtonLumoAI

## Installation Complète avec Démarrage Automatique

### 1️⃣ Préparation

```bash
cd ~/
git clone https://github.com/juli1roche/ProtonLumoAI.git
cd ProtonLumoAI
```

### 2️⃣ Configuration

Créez le fichier `.env` :

```bash
cp .env.example .env
nano .env
```

Remplissez :
```env
PROTON_BRIDGE_HOST=127.0.0.1
PROTON_BRIDGE_PORT=1143
PROTON_USERNAME=votre_email@pm.me
PROTON_PASSWORD=votre_mot_de_passe_bridge
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxxxxxxxx
```

### 3️⃣ Installation du Service Systemd

```bash
cd ~/ProtonLumoAI/systemd
chmod +x install-service.sh
./install-service.sh
```

**Ce que fait le script :**
- ✅ Crée l'environnement virtuel Python
- ✅ Installe les dépendances
- ✅ Configure le service systemd
- ✅ Active le démarrage automatique
- ✅ Active le linger (démarrage sans login)

### 4️⃣ Installation des Alias Fish (Optionnel)

```bash
cd ~/ProtonLumoAI/systemd
chmod +x setup-aliases.sh
./setup-aliases.sh
source ~/.config/fish/config.fish
```

### 5️⃣ Démarrer le Service

```bash
# Avec Fish aliases
lumo-start
lumo-status

# Ou directement
systemctl --user start protonlumoai
systemctl --user status protonlumoai
```

---

## 🔧 Commandes Essentielles

### Gestion du Service

```bash
# Démarrer
lumo-start              # ou: systemctl --user start protonlumoai

# Arrêter
lumo-stop               # ou: systemctl --user stop protonlumoai

# Redémarrer
lumo-restart            # ou: systemctl --user restart protonlumoai

# Statut
lumo-status             # ou: systemctl --user status protonlumoai

# Désactiver démarrage auto
lumo-disable            # ou: systemctl --user disable protonlumoai
```

### Logs

```bash
# Temps réel
lumo-logs               # ou: journalctl --user -u protonlumoai -f

# Erreurs uniquement
lumo-logs-errors        # ou: journalctl --user -u protonlumoai -p err

# Aujourd'hui
lumo-logs-today         # ou: journalctl --user -u protonlumoai --since today
```

### Monitoring

```bash
# Rapport complet
lumo-report

# Statistiques
lumo-stats

# Corrections apprises
lumo-corrections

# Patterns extraits
lumo-patterns
```

---

## 🔄 Redémarrage et Reprise

### Comportement au Redémarrage

1. **Laptop redémarre** 🔄
2. **Systemd démarre automatiquement** le service ⚡
3. **ProtonLumoAI charge le checkpoint** 💾
   ```json
   {
     "initial_scan_done": true,
     "processed_emails": ["INBOX:1234", ...],
     "last_check": {"INBOX": "2025-12-05T14:30:00"}
   }
   ```
4. **Reprend exactement où il s'était arrêté** ✅
5. **Traite uniquement les NOUVEAUX emails** 🎯

### Vérifier la Reprise

```bash
# Après redémarrage, vérifiez les logs
lumo-logs-today

# Vous devriez voir :
# ➡️  Reprise depuis checkpoint: 1247 emails déjà traités
# ✓ Scan initial terminé. Le système cherche les nouveaux emails.
```

---

## ⚠️ Dépannage

### Service ne Démarre Pas

```bash
# Vérifier le statut détaillé
systemctl --user status protonlumoai

# Voir les erreurs
journalctl --user -u protonlumoai -n 50 --no-pager

# Vérifier que ProtonMail Bridge tourne
ps aux | grep protonmail-bridge

# Redémarrer Bridge si nécessaire
systemctl --user restart protonmail-bridge
```

### Réinitialiser Complètement

```bash
# Arrêter le service
lumo-stop

# Réinitialiser le checkpoint
lumo-reset-checkpoint

# Optionnel : Réinitialiser l'apprentissage
lumo-reset-learning

# Redémarrer
lumo-start
```

### Désinstaller le Service

```bash
cd ~/ProtonLumoAI/systemd
chmod +x uninstall-service.sh
./uninstall-service.sh
```

---

## 🔒 Sécurité

Le service systemd inclut plusieurs protections :

- ✅ **NoNewPrivileges** - Pas d'élévation de privilèges
- ✅ **PrivateTmp** - Répertoire /tmp isolé
- ✅ **ProtectSystem** - Système en lecture seule
- ✅ **ProtectHome** - Home en lecture seule (sauf data/logs/config)
- ✅ **ReadWritePaths** - Accès écriture limité aux dossiers nécessaires

---

## 📊 Vérification de l'Installation

```bash
# Tout devrait être vert ✅
lumo-report
```

Sortie attendue :
```
📊 Statistiques ProtonLumoAI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔋 Service:
  ✅ Actif
  ✅ Démarrage auto activé

💾 Checkpoint:
  Emails traités: 1247
  Dernière mise à jour: 2025-12-05T14:35:00

🧠 Apprentissage:
  Corrections utilisateur: 15
  Règles expéditeur: 8
  Règles domaine: 3
  Mots-clés appris: 12
```

---

**✅ Installation terminée ! Le système démarrera automatiquement à chaque redémarrage.**