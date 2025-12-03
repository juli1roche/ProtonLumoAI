# 🚀 Guide de Démarrage Rapide - ProtonLumoAI

Commencez à automatiser vos emails en 5 minutes !

## 1️⃣ Installation (2 minutes)

```bash
# Aller dans le répertoire du projet
cd ~/ProtonLumoAI

# Lancer l'installation
bash scripts/install.sh

# Attendre la fin de l'installation...
# ✅ Installation terminée !
```

## 2️⃣ Configuration (1 minute)

```bash
# Éditer le fichier de configuration
nano .env
```

Remplir les deux champs obligatoires :

```env
PROTON_USERNAME=votre_email@proton.me
PROTON_PASSWORD=votre_mot_de_passe_bridge
```

**💡 Conseil** : Le mot de passe est celui généré par ProtonMail Bridge, visible dans l'application Bridge.

## 3️⃣ Vérification (30 secondes)

```bash
# Vérifier que tout est installé
fish scripts/check_dependencies.sh
```

Vous devriez voir :
```
✓ Python3 : OK
✓ Fish : OK
✓ Lumo CLI : OK (ou À installer)
✓ ProtonMail Bridge : OK
```

## 4️⃣ Démarrage (1 minute)

### Option A : Service systemd (recommandé)

```bash
# Démarrer le service
systemctl --user start proton-lumo-processor.service

# Activer le démarrage automatique
systemctl --user enable proton-lumo-processor.service

# Voir le statut
systemctl --user status proton-lumo-processor.service
```

### Option B : Lancement direct

```bash
# Lancer directement
python3 scripts/email_processor.py

# Ou avec l'alias Fish
lumo-run
```

## 5️⃣ Monitoring (30 secondes)

```bash
# Voir les logs en temps réel
tail -f logs/processor.log

# Ou avec l'alias
lumo-logs
```

Vous devriez voir :
```
[2024-01-15 10:30:00] INFO - Démarrage du service de tri Lumo...
[2024-01-15 10:30:01] INFO - Connexion établie
[2024-01-15 10:30:02] INFO - Traitement de la boîte de réception...
[2024-01-15 10:30:03] INFO - Email: Offre spéciale 50% -> VENTE (0.92)
[2024-01-15 10:30:04] INFO - ✓ Déplacé vers Achats
```

## 📋 Alias Fish Disponibles

Après l'installation, vous pouvez utiliser :

```bash
lumo-start      # Démarrer le service
lumo-stop       # Arrêter le service
lumo-restart    # Redémarrer le service
lumo-logs       # Voir les logs
lumo-status     # Voir le statut
lumo-check      # Vérifier les dépendances
lumo-run        # Lancer directement
lumo-train      # Entraîner le classifier
```

## 🎯 Catégories Automatiques

Le système classe automatiquement vos emails dans :

- 📧 **SPAM** → Dossier Spam
- 🛍️ **VENTE** → Dossier Achats
- 🏦 **BANQUE** → Dossier Administratif/Banque
- 💼 **PRO** → Dossier Travail
- ⚡ **URGENT** → Dossier À traiter
- ✈️ **VOYAGES** → Dossier Voyages
- 👥 **SOCIAL** → Dossier Réseaux sociaux
- 📰 **NEWSLETTER** → Dossier Newsletters

## 🧠 Améliorer la Classification

### Méthode 1 : Dossier d'Entraînement (Recommandé)

```bash
# Créer les dossiers d'entraînement dans ProtonMail
# Training/VENTE/
# Training/PRO/
# Training/BANQUE/
# etc.

# Déplacer les emails mal classés dans le bon dossier
# Le système apprendra automatiquement !
```

### Méthode 2 : Corrections Manuelles

```bash
# Créer un dossier "Corrections" dans ProtonMail
# Déplacer l'email mal classé dans Corrections
# Renommer le sujet : [CATEGORY] Original Subject
# Exemple : [PRO] Réunion importante

# Le système corrigera et apprendra automatiquement
```

## ⚙️ Configuration Avancée

### Changer l'Intervalle de Polling

```bash
# Dans le fichier .env
PROTON_LUMO_POLL_INTERVAL=30  # Vérifier toutes les 30 secondes
```

### Mode Dry-Run (Test)

```bash
# Les emails ne seront pas déplacés, juste classés
export PROTON_LUMO_DRY_RUN=true
python3 scripts/email_processor.py
```

### Traiter Tous les Emails

```bash
# Par défaut, seuls les emails non-lus sont traités
# Pour traiter tous les emails :
export PROTON_LUMO_UNSEEN_ONLY=false
python3 scripts/email_processor.py
```

## 🔍 Dépannage Rapide

### "ProtonMail Bridge non accessible"

```bash
# Vérifier que le service est actif
systemctl --user status protonmail-bridge.service

# Redémarrer le service
systemctl --user restart protonmail-bridge.service
```

### "Lumo CLI non trouvé"

```bash
# Installer Lumo CLI
paru -S lumo-cli

# Ou via npm
npm install -g @lumo/cli
```

### "Erreur de connexion IMAP"

```bash
# Vérifier les identifiants dans .env
nano .env

# Vérifier la connexion
telnet 127.0.0.1 1143
```

## 📊 Voir les Statistiques

```bash
# Voir les logs de classification
grep "Classification de l'email" logs/classifier.log

# Voir les rapports d'amélioration
ls -la logs/improvement_report_*.json

# Voir les métriques de performance
cat data/performance_metrics.json
```

## 🆘 Besoin d'Aide ?

1. **Vérifier les logs** :
   ```bash
   tail -f logs/processor.log
   ```

2. **Vérifier les dépendances** :
   ```bash
   fish scripts/check_dependencies.sh
   ```

3. **Consulter la documentation complète** :
   ```bash
   cat README.md
   ```

4. **Tester en mode dry-run** :
   ```bash
   export PROTON_LUMO_DRY_RUN=true
   python3 scripts/email_processor.py
   ```

## ✅ Checklist de Démarrage

- [ ] Installation complétée (`bash scripts/install.sh`)
- [ ] Fichier `.env` configuré avec identifiants
- [ ] Vérification des dépendances OK (`fish scripts/check_dependencies.sh`)
- [ ] Service démarré (`systemctl --user start proton-lumo-processor.service`)
- [ ] Logs visibles (`tail -f logs/processor.log`)
- [ ] Premiers emails classés et déplacés
- [ ] Dossiers d'entraînement créés pour amélioration

## 🎉 Prêt !

Votre système d'automatisation d'emails est maintenant opérationnel !

Les emails seront automatiquement classés et déplacés selon leur contexte.

Pour améliorer la classification, créez des dossiers d'entraînement et déplacez-y les emails mal classés.

---

**Besoin de plus d'informations ?** Consultez le `README.md` complet.

**Vous avez des questions ?** Vérifiez les logs : `lumo-logs`
