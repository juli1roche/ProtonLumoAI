# ProtonLumoAI - Système d'Automatisation Intelligente d'Emails

Un système complet d'automatisation pour classer et traiter vos emails ProtonMail avec le chatbot Lumo, en tenant compte de leur contexte (spam, vente, banques, professionnel, urgent, voyages, etc.).

## 🎯 Caractéristiques

- **Classification intelligente** : Utilise Lumo CLI avec fallback sur mots-clés
- **Entraînement continu** : Apprentissage automatique à partir de vos corrections
- **Auto-amélioration** : Évaluation automatique et amélioration des filtres
- **Intégration ProtonMail Bridge** : Accès direct à vos emails via IMAP
- **Fish Shell natif** : Configuration complète pour CachyOS avec Fish
- **Logging complet** : Suivi détaillé de toutes les opérations
- **Services systemd** : Démarrage automatique et gestion des services
- **Catégories contextuelles** : 8 catégories prédéfinies + extensibles

## 📋 Prérequis

### Système
- **OS** : CachyOS (Arch Linux)
- **Shell** : Fish shell (ou Bash)
- **Python** : 3.8+
- **Pacman** : Gestionnaire de paquets Arch

### Logiciels
- **ProtonMail Bridge** : Pour accéder à vos emails
- **Lumo CLI** (optionnel) : Pour la classification IA avancée
- **Git** : Pour le contrôle de version

## 🚀 Installation

### 1. Cloner ou télécharger le projet

```bash
cd ~/
git clone <repository_url> ProtonLumoAI
cd ProtonLumoAI
```

### 2. Exécuter l'installation

```bash
chmod +x scripts/install.sh
bash scripts/install.sh
```

L'installation va :
- Créer un environnement virtuel Python
- Installer les dépendances Python
- Créer les répertoires de configuration et de données
- Configurer les services systemd
- Configurer Fish shell

### 3. Vérifier les dépendances

```bash
fish scripts/check_dependencies.sh
```

Cela vérifie :
- ✓ Fish shell
- ✓ Python3 et pip3
- ✓ ProtonMail Bridge
- ✓ Lumo CLI (optionnel)
- ✓ Dépendances Python
- ✓ Outils système

### 4. Configurer les identifiants

Éditer le fichier `.env` :

```bash
nano .env
```

Remplir les champs :
```env
PROTON_USERNAME=votre_email@proton.me
PROTON_PASSWORD=votre_mot_de_passe_bridge
```

**Important** : Le mot de passe est celui généré par ProtonMail Bridge, pas votre mot de passe de compte.

## 📁 Structure du Projet

```
ProtonLumoAI/
├── scripts/
│   ├── install.sh                 # Script d'installation
│   ├── check_dependencies.sh       # Vérification des dépendances
│   ├── email_processor.py          # Processeur principal
│   ├── email_classifier.py         # Système de classification
│   ├── train_classifier.py         # Système d'entraînement
│   └── run.sh                      # Script de lancement
├── config/
│   ├── config.yaml                 # Configuration principale
│   ├── categories.json             # Catégories (généré)
│   └── env.fish                    # Configuration Fish (généré)
├── data/
│   ├── models/                     # Modèles d'IA
│   ├── training/                   # Exemples d'entraînement
│   └── cache/                      # Cache de classifications
├── logs/
│   ├── processor.log               # Logs du processeur
│   ├── classifier.log              # Logs du classifier
│   ├── trainer.log                 # Logs de l'entraîneur
│   └── dependency_check.log        # Logs de vérification
├── .env                            # Configuration d'environnement
└── README.md                        # Cette documentation
```

## ⚙️ Configuration

### Configuration Principale (config.yaml)

Le fichier `config/config.yaml` contient :

- **Bridge** : Paramètres de connexion ProtonMail Bridge
- **Processing** : Intervalle de polling, mode dry-run, etc.
- **Classification** : Seuils de confiance, méthodes
- **Training** : Paramètres d'entraînement automatique
- **Categories** : Définition des catégories et mots-clés
- **Logging** : Niveaux et formats de log

### Variables d'Environnement (.env)

```env
# ProtonMail Bridge
PROTON_BRIDGE_HOST=127.0.0.1
PROTON_BRIDGE_PORT=1143
PROTON_BRIDGE_SMTP_PORT=1025

# Identifiants (À CONFIGURER)
PROTON_USERNAME=votre_email@proton.me
PROTON_PASSWORD=votre_mot_de_passe_bridge

# Traitement
PROTON_LUMO_POLL_INTERVAL=60
PROTON_LUMO_AUTO_IMPROVE_INTERVAL=3600
PROTON_LUMO_UNSEEN_ONLY=true
PROTON_LUMO_DRY_RUN=false

# Logging
PROTON_LUMO_LOG_LEVEL=INFO
```

## 🎮 Utilisation

### Démarrage du Service

```bash
# Démarrer le service
systemctl --user start proton-lumo-processor.service

# Activer le démarrage automatique
systemctl --user enable proton-lumo-processor.service

# Voir le statut
systemctl --user status proton-lumo-processor.service

# Arrêter le service
systemctl --user stop proton-lumo-processor.service
```

### Alias Fish Shell

Après l'installation, les alias suivants sont disponibles :

```bash
lumo-start      # Démarrer le service
lumo-stop       # Arrêter le service
lumo-restart    # Redémarrer le service
lumo-logs       # Afficher les logs en temps réel
lumo-status     # Voir le statut du service
lumo-check      # Vérifier les dépendances
lumo-run        # Lancer le processeur directement
lumo-train      # Lancer l'entraînement manuel
```

### Mode Dry-Run

Pour tester sans déplacer les emails :

```bash
export PROTON_LUMO_DRY_RUN=true
python3 scripts/email_processor.py
```

### Entraînement Manuel

```bash
python3 scripts/train_classifier.py
```

## 📚 Catégories d'Emails

Le système reconnaît automatiquement les catégories suivantes :

| Catégorie | Dossier | Mots-clés | Priorité |
|-----------|---------|-----------|----------|
| **SPAM** | Spam | unsubscribe, click here, limited time | 1 |
| **VENTE** | Achats | solde, promo, offrir, % | 2 |
| **BANQUE** | Administratif/Banque | virement, compte, facture | 3 |
| **PRO** | Travail | réunion, projet, client, deadline | 4 |
| **URGENT** | À traiter | urgent, asap, important | 5 |
| **VOYAGES** | Voyages | billet, train, vol, booking | 2 |
| **SOCIAL** | Réseaux sociaux | like, comment, follow | 1 |
| **NEWSLETTER** | Newsletters | newsletter, digest, subscribe | 1 |

## 🧠 Système d'Apprentissage

### Entraînement Automatique

Le système apprend automatiquement de vos corrections :

1. **Créer un dossier d'entraînement** :
   ```
   Training/VENTE/
   Training/PRO/
   Training/BANQUE/
   etc.
   ```

2. **Déplacer les emails mal classés** dans le bon dossier d'entraînement

3. **Le système apprend** automatiquement lors du cycle d'amélioration

### Corrections Manuelles

Pour corriger une classification :

1. Créer un dossier `Corrections/`
2. Déplacer l'email mal classé dans ce dossier
3. Renommer le sujet : `[CATEGORY] Original Subject`
   - Exemple : `[PRO] Réunion importante`

### Évaluation de Performance

Le système évalue automatiquement sa performance :

- **Accuracy** : Pourcentage global de bonnes classifications
- **Precision** : Pourcentage de vraies positives par catégorie
- **Recall** : Pourcentage de positives détectées
- **F1-Score** : Moyenne harmonique de precision et recall

Les métriques sont sauvegardées dans `data/performance_metrics.json`

## 📊 Monitoring et Logs

### Voir les Logs

```bash
# Logs du processeur (temps réel)
tail -f logs/processor.log

# Logs du classifier
tail -f logs/classifier.log

# Logs de l'entraîneur
tail -f logs/trainer.log

# Tous les logs
tail -f logs/*.log
```

### Rapports d'Amélioration

Les rapports d'amélioration sont sauvegardés dans :
```
logs/improvement_report_YYYYMMDD_HHMMSS.json
```

Contenu :
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "training": {
    "total_processed": 42,
    "by_category": {"VENTE": 15, "PRO": 10, ...}
  },
  "corrections": {
    "total_corrections": 5,
    "by_category": {"VENTE": 3, "PRO": 2}
  },
  "evaluation": {
    "accuracy": 0.92,
    "by_category": {...}
  },
  "status": "success"
}
```

## 🔧 Dépannage

### ProtonMail Bridge non accessible

```bash
# Vérifier le service
systemctl --user status protonmail-bridge.service

# Redémarrer le service
systemctl --user restart protonmail-bridge.service

# Vérifier la connexion
telnet 127.0.0.1 1143
```

### Lumo CLI non trouvé

```bash
# Installer Lumo CLI
paru -S lumo-cli

# Ou via npm
npm install -g @lumo/cli

# Vérifier l'installation
lumo --version
```

### Erreurs de connexion IMAP

1. Vérifier les identifiants dans `.env`
2. Vérifier que ProtonMail Bridge est en cours d'exécution
3. Vérifier que le port 1143 est accessible
4. Vérifier les logs : `tail -f logs/processor.log`

### Performance lente

1. Augmenter `PROTON_LUMO_POLL_INTERVAL`
2. Réduire `PROTON_LUMO_AUTO_IMPROVE_INTERVAL`
3. Vérifier les ressources système : `top`, `htop`
4. Vérifier la connexion réseau

## 🔐 Sécurité

### Bonnes Pratiques

1. **Ne pas commiter le fichier `.env`** : Ajouter à `.gitignore`
2. **Utiliser des variables d'environnement** pour les secrets
3. **Restreindre les permissions** :
   ```bash
   chmod 600 .env
   chmod 700 scripts/*.sh
   ```
4. **Utiliser un mot de passe Bridge** et non votre mot de passe de compte
5. **Vérifier les logs** régulièrement pour détecter les anomalies

## 📈 Améliorations Futures

- [ ] Interface web de monitoring
- [ ] Support de multiples comptes ProtonMail
- [ ] Intégration avec d'autres fournisseurs d'email
- [ ] Machine Learning avancé (neural networks)
- [ ] API REST pour l'intégration
- [ ] Support de règles personnalisées
- [ ] Notification en temps réel
- [ ] Backup automatique des configurations

## 🤝 Contribution

Les contributions sont bienvenues ! Pour contribuer :

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support

Pour toute question ou problème :

1. Vérifier les logs : `tail -f logs/processor.log`
2. Exécuter la vérification des dépendances : `fish scripts/check_dependencies.sh`
3. Consulter la documentation : `README.md`
4. Ouvrir une issue sur GitHub

## 🙏 Remerciements

- **ProtonMail** pour ProtonMail Bridge
- **Lumo AI** pour le chatbot de classification
- **CachyOS** pour la distribution Arch optimisée
- **Fish Shell** pour le shell moderne

## 📅 Changelog

### v1.0.0 (Initial Release)
- ✓ Système de classification avec Lumo CLI
- ✓ Entraînement automatique
- ✓ Auto-amélioration continue
- ✓ Intégration ProtonMail Bridge
- ✓ Configuration Fish shell
- ✓ Services systemd
- ✓ Logging complet
- ✓ 8 catégories prédéfinies

---

**ProtonLumoAI** - Automatisez votre gestion d'emails avec l'IA 🚀
