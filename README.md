# 🤖 ProtonLumoAI

**Système de tri automatique intelligent d'emails ProtonMail avec apprentissage adaptatif**

[![Version](https://img.shields.io/badge/version-1.1.1-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## 🌟 Caractéristiques

### ✨ Fonctionnalités Principales

- **🧠 Classification IA via Perplexity API** - Classification intelligente multi-catégories
- **📄 Executive Summary** - Rapports quotidiens des messages importants (3x/jour)
- **🔍 Détection Intelligente** - Scoring multi-critères (urgence, contacts, domaines, relocation)
- **🔄 Apprentissage Adaptatif** - Détection automatique des déplacements manuels
- **🎈 Few-Shot Learning** - Amélioration continue basée sur vos corrections
- **💾 Persistance Checkpoint** - Reprise intelligente après redémarrage
- **👁 Préservation du Statut** - Les emails non lus restent non lus après tri
- **⚡ Performance** - Traitement batch avec limitation anti-surcharge
- **🔒 Sécurité** - Connexion STARTTLS avec ProtonMail Bridge

### 🔴 Executive Summary Feature (v1.1.0)

**Rapports automatiques des messages importants**

- **Horaire**: 09:00 AM, 13:00 PM, 17:00 PM CET (configurable)
- **Détection**: Scoring multi-critères (urgence, contacts clés, domaines, mots-clés)
- **Rapports**: Format HTML avec action types (RESPOND, VERIFY, TRACK, REVIEW)
- **Stockage**: Emails non lus dans dossier `Folders/Exec-Summary`
- **Contexte**: Spécifiquement configuré pour votre relocation en Ecosse

Voir [docs/EXECUTIVE_SUMMARY.md](docs/EXECUTIVE_SUMMARY.md) pour détails complets.

### 🏎 Catégories Par Défaut

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

Copiez le fichier template et remplissez vos credentials :

```bash
cp .env.example .env
nano .env
```

**Variables critiques à définir :**

```env
# ProtonMail Bridge (utilisez le mot de passe Bridge, PAS votre mot de passe compte)
PROTON_USERNAME=votre_email@pm.me
PROTON_PASSWORD=votre_mot_de_passe_bridge

# Perplexity API
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxxxxxxxx

# Executive Summary (optionnel mais recommandé)
PROTON_LUMO_SUMMARY_ENABLED=true
PROTON_LUMO_SUMMARY_EMAIL=votre_email@pm.me
PROTON_LUMO_IMPORTANT_CONTACTS=contact1@example.com,contact2@example.com
```

Voir [.env.example](.env.example) pour toutes les options disponibles.

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
python scripts/email_processor.py
```

---

## 🔧 Configuration

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

### Executive Summary - Contacts Importants

Ajoutez des contacts dans `.env` :

```env
PROTON_LUMO_IMPORTANT_CONTACTS=brigitte@clavel.fr,frederic@roche.fr,paul@cirrus.com
```

### Executive Summary - Mots-clés Relocation

Personnalisez pour votre contexte :

```env
PROTON_LUMO_RELOCATION_KEYWORDS=scotland,visa,relocation,edinburgh,school,enrollment
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

# Voir les rapports Executive Summary
ls -lh ~/ProtonLumoAI/data/summary_*.html | tail -3
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
  ✚ Règle expéditeur: john@entreprise.com → PRO
  ✚ Règle domaine: @entreprise.com → PRO
  ✚ Mot-clé sujet: "réunion" → PRO

🏎 Prochains emails de john@entreprise.com:
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
│   ├── main.py                      # Point d'entrée principal
│   ├── email_processor.py          # Processeur IMAP + orchestration
│   ├── email_classifier.py         # Classification IA (Perplexity)
│   ├── important_message_detector.py  # Détection messages importants
│   ├── summary_email_reporter.py    # Rapports Executive Summary
│   ├── adaptive_learner.py         # Apprentissage adaptatif
│   ├── email_parser.py             # Parsing emails (UTF-8, HTML)
│   ├── feedback_manager.py         # Gestion feedback utilisateur
│   └── sync_folders.py             # Synchronisation dossiers ProtonMail
├── data/
│   ├── checkpoint.json             # Checkpoint persistance
│   ├── important_messages.json     # Messages importants détectés
│   ├── learning/
│   │   ├── user_corrections.jsonl     # Corrections utilisateur
│   │   ├── learned_patterns.json      # Patterns appris
│   │   └── email_signatures.json      # Signatures emails
│   └── training/
├── config/
│   └── categories.json             # Catégories sync ProtonMail
└── docs/
    └── EXECUTIVE_SUMMARY.md        # Executive Summary documentation
```

---

## 🔒 Dépannage

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

### "Identifiants manquants" au démarrage

**Cause**: Le fichier `.env` n'est pas chargé correctement ou les variables sont mal nommées.

**Solution**:
1. Vérifiez que `.env` existe : `ls -la ~/ProtonLumoAI/.env`
2. Vérifiez les variables requises :
   ```bash
   grep -E "PROTON_USERNAME|PROTON_PASSWORD" ~/ProtonLumoAI/.env
   ```
3. Assurez-vous d'utiliser le **mot de passe Bridge**, pas votre mot de passe ProtonMail
4. Ouvrez ProtonMail Bridge → Paramètres du compte → IMAP/SMTP Settings pour récupérer le mot de passe

### Réinitialiser le Checkpoint

```bash
# Si besoin de recommencer from scratch
rm ~/ProtonLumoAI/data/checkpoint.json
fish run.fish
```

### Rapports Executive Summary Non Générés

Voir la section **Troubleshooting** dans [docs/EXECUTIVE_SUMMARY.md](docs/EXECUTIVE_SUMMARY.md).

---

## 🤝 Contribution & Collaboration

**Les contributions sont les bienvenues !** Ce projet est en développement actif et nous recherchons spécifiquement de l'aide sur :

### 🎯 Domaines Prioritaires

#### 🧠 Machine Learning & Classification
- **Amélioration de l'apprentissage adaptatif**
  - Implémentation de modèles locaux (sklearn, transformers)
  - Fine-tuning de modèles de langage pour classification d'emails
  - Réduction de la dépendance à l'API Perplexity (coût)
  - Active learning avec feedback utilisateur

- **Optimisation du scoring multi-critères**
  - Amélioration des poids de scoring pour Executive Summary
  - Détection d'anomalies (phishing, urgences)
  - Clustering automatique de nouveaux types d'emails

#### 🔍 Filtrage & Détection
- **Anti-spam avancé**
  - Intégration de modèles anti-spam (SpamAssassin, Rspamd)
  - Détection de phishing par analyse de liens
  - Validation SPF/DKIM/DMARC

- **Extraction d'entités**
  - NER (Named Entity Recognition) pour contacts/dates/lieux
  - Extraction automatique d'actions (RDV, deadlines, paiements)
  - Génération de rappels intelligents

### 📝 Comment Contribuer

1. **Fork** le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une **Pull Request**

### 💬 Discussion & Support

- **Issues GitHub** : Pour bugs, features requests, questions
- **Discussions** : Pour idées, brainstorming, architecture
- **Email** : juli1.roche@gmail.com (collaboration sérieuse uniquement)

### 🎓 Bon Premier Problème

Cherchez les issues taggées `good first issue` ou `help wanted` :
- Amélioration de la documentation
- Ajout de tests unitaires
- Optimisation de performances
- Traduction (EN → FR, FR → EN)

---

## 📝 Changelog

Voir [CHANGELOG.md](CHANGELOG.md) pour l'historique complet des versions.

**v1.1.1** - Configuration Fixes & Systemd Compatibility (2025-12-08)
**v1.1.0** - Executive Summary Feature (2025-12-06)
**v1.0.2** - IMAP Parsing Fix & Production Ready (2025-12-05)
**v1.0.1** - Filter Optimization (2025-12-05)
**v1.0.0** - Initial Release (2025-12-05)

---

## 📋 Licence

Distribué sous licence MIT. Voir `LICENSE` pour plus d'informations.

---

## 👤 Auteur

**Julien Roche** - Lead Analog Designer & AI Enthusiast

- Portfolio: [julien-roche-portfolio.netlify.app](https://julien-roche-portfolio.netlify.app/)
- GitHub: [@juli1roche](https://github.com/juli1roche)
- Location: Aix-en-Provence 🇫🇷 → Edinburgh 🇬🇧 (Jan 2026)

---

## 🚀 Roadmap

### Court Terme (Q1 2026)
- [ ] 🧠 Modèle local sklearn/transformers (réduction coûts API)
- [ ] 🔍 Anti-spam avancé avec détection phishing
- [ ] 📊 Dashboard web pour monitoring et configuration
- [ ] 🐳 Docker container pour déploiement facile
- [ ] 🧐 Tests unitaires complets (pytest)

### Moyen Terme (Q2-Q3 2026)
- [ ] 👥 Support multi-comptes email
- [ ] 📤 Export statistiques (CSV, JSON, Grafana)
- [ ] 🔔 Notifications Slack/Teams pour emails urgents
- [ ] 🌐 API REST pour intégrations tierces
- [ ] 📚 Documentation anglaise complète

### Long Terme (2026+)
- [ ] 🌎 Intégration Gmail, Outlook, autres providers
- [ ] 🤖 Mode "apprentissage assisté" avec UI interactive
- [ ] 📱 Application mobile (notifications push)
- [ ] 📅 Intégration calendrier (extraction RDV automatique)
- [ ] 🤝 Marketplace de règles partagées entre utilisateurs

---

## ⭐ Star History

Si ce projet vous a été utile, n'hésitez pas à lui donner une étoile ! ⭐

---

**Made with ❤️ and 🤖 AI** | ProtonLumoAI v1.1.1
