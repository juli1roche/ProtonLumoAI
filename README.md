# 🤖 ProtonLumoAI

**Système de tri automatique intelligent d'emails ProtonMail avec apprentissage adaptatif**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🎯 Caractéristiques

### ✨ Fonctionnalités Principales

- **🧠 Classification IA via Perplexity API** - Classification intelligente multi-catégories
- **🔄 Apprentissage Adaptatif** - Détection automatique des déplacements manuels et apprentissage
- **🎯 Few-Shot Learning** - Amélioration continue basée sur vos corrections
- **💾 Persistance Checkpoint** - Reprise intelligente après redémarrage
- **👁️ Préservation du Statut** - Les emails non lus restent non lus après tri
- **⚡ Performance** - Traitement batch avec limitation anti-surcharge
- **🔒 Sécurité** - Connexion STARTTLS avec ProtonMail Bridge

### 🎨 Catégories Par Défaut

| Catégorie | Dossier Cible | Description |
|-----------|---------------|-------------|
| **PRO** | `Folders/Travail` | Emails professionnels, réunions, projets |
| **BANQUE** | `Folders/Administratif/Banque` | Virements, factures, transactions |
| **VENTE** | `Folders/Achats` | Promotions, commandes, achats |
| **VOYAGES** | `Folders/Voyages` | Billets, réservations, itinéraires |
| **NEWSLETTER** | `Folders/Newsletters` | Newsletters, digests hebdomadaires |
| **SOCIAL** | `Folders/Reseaux_sociaux` | Notifications réseaux sociaux |
| **URGENT** | `Folders/A_traiter` | Emails marqués urgents ou importants |
| **SPAM** | `Spam` | Publicités, emails non sollicités |

---

## 🚀 Installation

### Prérequis

- **Python 3.9+**
- **ProtonMail Bridge** installé et configuré
- **Compte Perplexity API** ([créer un compte](https://www.perplexity.ai/))
- **Fish Shell** (optionnel, pour le script de lancement)

### Étape 1 : Cloner le Répertoire

```bash
git clone https://github.com/juli1roche/ProtonLumoAI.git
cd ProtonLumoAI
```

### Étape 2 : Configuration de l'Environnement

Créez un fichier `.env` à la racine :

```env
# ProtonMail Bridge
PROTON_BRIDGE_HOST=127.0.0.1
PROTON_BRIDGE_PORT=1143
PROTON_USERNAME=votre_email@pm.me
PROTON_PASSWORD=votre_mot_de_passe_bridge

# Perplexity API
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxxxxxxxx

# Configuration (optionnel)
PROTON_LUMO_POLL_INTERVAL=60          # Intervalle de scan en secondes
PROTON_LUMO_UNSEEN_ONLY=true         # Traiter uniquement les non-lus
PROTON_LUMO_DRY_RUN=false             # Mode test sans déplacement réel
PROTON_LUMO_MAX_EMAILS_PER_FOLDER=100 # Limite par dossier pour éviter surcharge
```

### Étape 3 : Installation des Dépendances

**Avec Fish Shell :**
```fish
fish run.fish
```

**Ou manuellement :**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/sync_folders.py
python scripts/main.py
```

---

## 🛠️ Configuration

### Personnaliser les Catégories

Éditez `scripts/email_classifier.py` :

```python
DEFAULT_CATEGORIES = {
    "MA_CATEGORIE": EmailCategory(
        name="MA_CATEGORIE",
        folder="Folders/MonDossier",
        keywords=["mot1", "mot2", "mot3"],
        confidence_threshold=0.7,
        priority=3,
        description="Description de ma catégorie"
    ),
}
```

### Ajuster les Performances

```env
# Traitement plus rapide (plus d'appels API)
PROTON_LUMO_POLL_INTERVAL=30
PROTON_LUMO_MAX_EMAILS_PER_FOLDER=200

# Traitement plus lent (économie API)
PROTON_LUMO_POLL_INTERVAL=300
PROTON_LUMO_MAX_EMAILS_PER_FOLDER=50
```

---

## 🎮 Utilisation

### Lancement Standard

```bash
fish run.fish
```

### Arrêt Propre

```bash
# Appuyez sur Ctrl+C
# Le checkpoint est automatiquement sauvegardé
```

### Monitoring

```bash
# Voir les logs en temps réel
tail -f ~/ProtonLumoAI/logs/email_processor.log

# Statistiques de classification
grep "✓ Déplacé vers" ~/ProtonLumoAI/logs/email_processor.log | wc -l

# Catégories les plus utilisées
grep "Perplexity:" ~/ProtonLumoAI/logs/email_processor.log | awk '{print $6}' | sort | uniq -c | sort -rn
```

---

## 🧠 Apprentissage Adaptatif

### Comment ça Marche ?

1. **Détection Automatique** : Le système détecte quand vous déplacez manuellement un email
2. **Apprentissage** : Il extrait des patterns (expéditeur, domaine, mots-clés)
3. **Amélioration** : Les prochains emails similaires sont automatiquement classés correctement

### Exemple Concret

```
📧 Email reçu: "Réunion Q4" de john@entreprise.com
└─ IA classe en: NEWSLETTER (confiance: 0.65)
👉 Vous déplacez vers: Folders/Travail

🧠 Système apprend:
  ➕ Règle expéditeur: john@entreprise.com → PRO
  ➕ Règle domaine: @entreprise.com → PRO
  ➕ Mot-clé sujet: "réunion" → PRO

🎯 Prochains emails de john@entreprise.com:
  → Automatiquement classés en PRO (confiance: 0.95)
```

### Visualiser l'Apprentissage

```bash
# Voir les corrections apprises
cat ~/ProtonLumoAI/data/learning/user_corrections.jsonl | jq .

# Voir les règles extraites
cat ~/ProtonLumoAI/data/learning/learned_patterns.json | jq .
```

---

## 📊 Architecture

```
ProtonLumoAI/
├── scripts/
│   ├── main.py                  # Point d'entrée principal
│   ├── email_processor.py       # Processeur IMAP + orchestration
│   ├── email_classifier.py      # Classification IA (Perplexity)
│   ├── adaptive_learner.py      # Apprentissage adaptatif
│   ├── email_parser.py          # Parsing emails (UTF-8, HTML)
│   ├── feedback_manager.py      # Gestion feedback utilisateur
│   └── sync_folders.py          # Synchronisation dossiers ProtonMail
├── data/
│   ├── checkpoint.json          # Checkpoint persistance
│   ├── learning/
│   │   ├── user_corrections.jsonl  # Corrections utilisateur
│   │   ├── learned_patterns.json   # Patterns appris
│   │   └── email_signatures.json   # Signatures emails
│   └── training/
└── config/
    └── categories.json          # Catégories sync ProtonMail
```

---

## 🔧 Dépannage

### ProtonMail Bridge Non Connecté

```bash
# Vérifier que Bridge est actif
ps aux | grep protonmail-bridge

# Tester la connexion IMAP
telnet 127.0.0.1 1143
```

### Erreurs API Perplexity

```bash
# Vérifier la clé API
echo $PERPLEXITY_API_KEY

# Tester l'API manuellement
curl https://api.perplexity.ai/chat/completions \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"sonar","messages":[{"role":"user","content":"test"}]}'
```

### Réinitialiser le Checkpoint

```bash
# Si besoin de recommencer from scratch
rm ~/ProtonLumoAI/data/checkpoint.json
fish run.fish
```

---

## 📝 Changelog

Voir [CHANGELOG.md](CHANGELOG.md) pour l'historique complet des versions.

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Veuillez :

1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📜 Licence

Distribué sous licence MIT. Voir `LICENSE` pour plus d'informations.

---

## 👤 Auteur

**Julien Roche** - Lead Analog Designer & AI Enthusiast

- Portfolio: [julien-roche-portfolio.netlify.app](https://julien-roche-portfolio.netlify.app/)
- GitHub: [@juli1roche](https://github.com/juli1roche)
- Location: Aix-en-Provence, France 🇫🇷

---

## 🚀 Roadmap

- [ ] Interface Web pour configuration et monitoring
- [ ] Support multi-comptes email
- [ ] Export des statistiques (CSV, JSON)
- [ ] Intégration avec d'autres providers (Gmail, Outlook)
- [ ] Modèle local fine-tuné (sklearn/transformers)
- [ ] API REST pour intégrations tierces
- [ ] Docker container pour déploiement facile
- [ ] Mode "apprentissage assisté" avec UI

---

## ⭐ Star History

Si ce projet vous a été utile, n'hésitez pas à lui donner une étoile ! ⭐

---

**Made with ❤️ and 🤖 AI** | ProtonLumoAI v1.0.0