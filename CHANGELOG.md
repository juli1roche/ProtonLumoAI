# Changelog

Toutes les modifications notables de ProtonLumoAI sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère à [Semantic Versioning](https://semver.org/lang/fr/).

---

## [1.0.0] - 2025-12-05

### ✨ Ajouté

#### Système d'Apprentissage Adaptatif
- **🧠 Adaptive Learner** (`adaptive_learner.py`)
  - Détection automatique des déplacements manuels d'emails
  - Extraction de patterns (expéditeur, domaine, mots-clés)
  - Few-shot learning pour amélioration du prompt Perplexity
  - Système de règles appris avec confiance (0.75-0.95)
  - Persistance des corrections et patterns appris

#### Persistance et Reprise
- **💾 Checkpoint System**
  - Sauvegarde automatique de l'état (checkpoint.json)
  - Reprise intelligente après redémarrage
  - Évite le retraitement des emails déjà classés
  - Préservation du flag SEEN (non-lus restent non-lus)

#### Classification IA
- **⚡ Perplexity API Integration**
  - Remplacement de Lumo CLI par API Perplexity directe
  - Validation stricte des catégories retournées
  - Prompt enrichi avec descriptions et exemples
  - System prompt renforcé contre les catégories invalides
  - Few-shot learning intégré au prompt

#### Infrastructure
- **🔧 Namespace Folders/ Fix**
  - Correction des chemins de dossiers (utilisation de `Folders/`)
  - Support de la création récursive de dossiers
  - Validation de l'existence des dossiers avant déplacement
  
### 🔧 Corrigé

#### Erreurs de Classification
- **✅ Validation des Catégories**
  - Correction du bug `[TRYCREATE] no such mailbox`
  - Élimination des catégories invalides retournées par l'IA
  - Fallback automatique sur mots-clés si catégorie invalide

#### Gestion des Dossiers
- **📁 ProtonMail Folder Structure**
  - Utilisation correcte du namespace `Folders/` pour les nouveaux dossiers
  - Suppression des accents et espaces dans les noms de dossiers
  - Cache de dossiers existants pour éviter recréation

#### Performance
- **⚡ Limitation Anti-Surcharge**
  - Limite par défaut de 100 emails/dossier (configurable)
  - Évite l'explosion du coût API Perplexity
  - Traitement batch optimisé

### 🔄 Modifié

#### email_classifier.py
- Refactoring de `classify_with_lumo()` vers Perplexity API
- Ajout de `DEFAULT_CATEGORIES` avec chemins `Folders/` corrects
- Fallback amélioré sur classification par mots-clés
- Intégration du few-shot learning

#### email_processor.py
- Ajout du système de checkpoint persistant
- Préservation du flag SEEN lors des déplacements
- Détection des emails déjà traités (pas de retraitement)
- Sauvegarde automatique du checkpoint toutes les 60s

### 📚 Documentation

- **README.md** complet et professionnel
- **CHANGELOG.md** (ce fichier)
- Architecture claire et compréhensible
- Exemples d'utilisation concrets
- Section troubleshooting détaillée

---

## Types de Changements

- **✨ Ajouté** pour les nouvelles fonctionnalités.
- **🔄 Modifié** pour les changements aux fonctionnalités existantes.
- **🗑️ Obsolète** pour les fonctionnalités qui seront retirées dans les prochaines versions.
- **🚫 Retiré** pour les fonctionnalités supprimées.
- **🔧 Corrigé** pour les corrections de bugs.
- **🔒 Sécurité** pour les corrections de vulnérabilités.