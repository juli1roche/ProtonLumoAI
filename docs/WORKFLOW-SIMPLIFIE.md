# ⚡ WORKFLOW SIMPLIFIÉ - Pré-tri Auto + Affinage Manual + Apprentissage

## 🎯 Plan Exécution (2-3 heures total)

### ÉTAPE 1: Pré-tri Automatique (15 min)

```bash
cd ~/ProtonLumoAI

# Vérifier la connexion
python test_imap_connection.py
# ✓ Doit afficher: Connected successfully

# Exécuter le pré-tri automatique
python scripts/pretri_folders_2025_and_gmail.py

# Ça va:
# - Analyser 100 derniers emails de Folders/2025 et Gmail
# - Créer automatiquement: /PRO, /FINANCE, /NEWSLETTER, /COMMERCE, /VOYAGE
# - Déplacer les emails par catégories intelligentes
# - Générer un rapport

# Vous verrez:
# 🤖 PRÉ-TRI AUTOMATIQUE - Folders/2025 et Gmail
# 📁 Analysing Folders/2025...
# ✅ PRÉ-TRI TERMINÉ
```

### ÉTAPE 2: Vérifier le Pré-tri (5 min)

```bash
# Voir le rapport
cat ~/ProtonLumoAI/data/learning/pretri_rapport.json | jq .

# Voir le résumé de catégories
jq '.categories_detectees' ~/ProtonLumoAI/data/learning/pretri_rapport.json

# Exemple de résultat:
# {
#   "Folders/2025": {
#     "PRO": 18,
#     "FINANCE": 12,
#     "NEWSLETTER": 15,
#     "COMMERCE": 10,
#     "VOYAGE": 8,
#     "MIXED": 37
#   },
#   "Gmail": {
#     "PRO": 12,
#     "FINANCE": 8,
#     "PERSONNEL": 10,
#     "MIXED": 20
#   }
# }
```

### ÉTAPE 3: Affinage MANUEL dans ProtonMail (30-45 min)

**ARRÊTER le processeur ProtonLumoAI pendant cette étape:**

```bash
# Dans le terminal où run.fish tourne:
Ctrl+C
```

**DANS PROTONMAIL (Web UI ou Client):**

1. Vérifier la structure créée:
   - Folders/2025/PRO (doit avoir 18 emails)
   - Folders/2025/FINANCE (12 emails)
   - Folders/2025/NEWSLETTER (15 emails)
   - Folders/2025/COMMERCE (10 emails)
   - Folders/2025/VOYAGE (8 emails)
   - Gmail/PRO (12 emails)
   - Gmail/FINANCE (8 emails)
   - Gmail/PERSONNEL (10 emails)

2. POUR CHAQUE dossier:
   - Ouvrir Folders/2025/PRO
   - Vérifier que ce sont des emails PRO
   - Si erreurs: drag & drop vers la bonne catégorie
   - Si manquent des emails PRO: les chercher et les déplacer
   - OBJECTIF: 35-40 emails bien classés par dossier
   - Répéter pour FINANCE, NEWSLETTER, COMMERCE, VOYAGE

3. Faire la même chose pour Gmail

### ÉTAPE 4: Lancer le Processeur (5 min)

```bash
# Une fois satisfait du tri manuel:
# Redémarrer le processeur ProtonLumoAI
fish run.fish

# OU si c'est un service systemd:
# sudo systemctl start proton-lumoai
```

### ÉTAPE 5: Lancer L'Apprentissage (10 min)

```bash
# Dans un AUTRE terminal:
cd ~/ProtonLumoAI

# Vérifier la limite (devrait être 10, pas 100)
grep PROTON_LUMO_LEARNING_EMAILS_PER_FOLDER .env

# Si c'est 100, revenir à 10:
echo "Removing PROTON_LUMO_LEARNING_EMAILS_PER_FOLDER=100 if exists..."
sed -i '/^PROTON_LUMO_LEARNING_EMAILS_PER_FOLDER=100$/d' .env

# Ajouter si absent:
grep -q "PROTON_LUMO_LEARNING" .env || echo 'PROTON_LUMO_LEARNING_ENABLED=true' >> .env

# Lancer l'apprentissage
python scripts/sync_and_learn.py

# Ça va apprendre de vos sous-dossiers créés!
# Vous verrez:
# 🤖 Starting folder learning analysis...
# 📁 Analyzing Folders/2025/PRO
# 📁 Analyzing Folders/2025/FINANCE
# ✅ Learning analysis complete!
```

### ÉTAPE 6: Vérifier les Résultats (5 min)

```bash
# Voir tous les dossiers et leur confiance
jq '[.[] | {folder: .folder_name, emails: .email_count, confiance: (.confidence * 100 | floor)}]' \
  ~/ProtonLumoAI/data/learning/folder_patterns.json | jq 'sort_by(.confiance) | reverse'

# Voir spécifiquement les sous-dossiers créés
jq '.[] | select(.folder_name | contains("PRO") or contains("FINANCE"))' \
  ~/ProtonLumoAI/data/learning/folder_patterns.json

# Voir les patterns des nouveaux sous-dossiers
echo "=== Patterns PRO ==="
jq '."Folders/2025/PRO" | {emails:.email_count, confiance:.confidence, top_keywords:.common_keywords | keys[0:5]}' \
  ~/ProtonLumoAI/data/learning/folder_patterns.json

echo "\n=== Patterns FINANCE ==="
jq '."Folders/2025/FINANCE" | {emails:.email_count, confiance:.confidence, top_keywords:.common_keywords | keys[0:5]}' \
  ~/ProtonLumoAI/data/learning/folder_patterns.json
```

---

## 📊 Timeline Estimée

| Étape | Durée | Actions |
|-------|-------|----------|
| **1. Pré-tri Auto** | 15 min | `python scripts/pretri_folders_2025_and_gmail.py` |
| **2. Vérifier** | 5 min | Voir le rapport |
| **3. Affinage Manuel** | 30-45 min | Drag & drop dans ProtonMail |
| **4. Redémarrer** | 5 min | `fish run.fish` |
| **5. Apprentissage** | 10 min | `python scripts/sync_and_learn.py` |
| **6. Vérification** | 5 min | `jq` sur folder_patterns.json |
| **TOTAL** | **70-90 min** | **~1.5 heures** |

---

## 🎁 Résultats Attendus

### Après ÉTAPE 3 (Affinage Manuel)
```
✅ Folders/2025/
   ├─ PRO/ (35 emails bien classés)
   ├─ FINANCE/ (25 emails bien classés)
   ├─ NEWSLETTER/ (20 emails bien classés)
   ├─ COMMERCE/ (15 emails bien classés)
   ├─ VOYAGE/ (10 emails bien classés)
   └─ [Reste: 0-5 emails non classés]

✅ Gmail/
   ├─ PRO/ (20 emails)
   ├─ FINANCE/ (12 emails)
   ├─ PERSONNEL/ (15 emails)
   └─ [Reste: 3-5 emails]
```

### Après ÉTAPE 5 (Apprentissage)
```
📊 Folder Patterns:
Folders/2025/PRO - Confiance: 95%
Folders/2025/FINANCE - Confiance: 92%
Folders/2025/NEWSLETTER - Confiance: 98%
Folders/2025/COMMERCE - Confiance: 89%
Folders/2025/VOYAGE - Confiance: 91%
Gmail/PRO - Confiance: 93%
Gmail/FINANCE - Confiance: 88%
Gmail/PERSONNEL - Confiance: 94%

➡️ Confiance moyenne: 92%
```

---

## 🎁 Avantages de ce Workflow

✅ **Pré-tri automatique** = Gain de temps
✅ **Affinage manuel** = Parfait pour votre cas spécifique
✅ **Apprentissage optimisé** = Commence avec bonne structure
✅ **Rapide** = 1.5h au total
✅ **Résultat** = 92%+ de précision immédiatement
✅ **Continu** = Meilleure précision chaque jour

---

## 🚀 Commencez!

**EXÉCUTEZ MAINTENANT:**

```bash
cd ~/ProtonLumoAI
python scripts/pretri_folders_2025_and_gmail.py
```

**Et suivez les Étapes ci-dessus!** 🎯
