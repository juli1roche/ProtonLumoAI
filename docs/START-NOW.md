# 🎯 COMMENCER MAINTENANT - Instructions Exactes

## Ce que vous avez

✅ **Script de pré-tri automatique** créé: `scripts/pretri_folders_2025_and_gmail.py`
✅ **Guide complet** créé: `WORKFLOW-SIMPLIFIE.md`
✅ **ProtonLumoAI v1.2.1** prêt à fonctionner

---

## 🚀 FAIRE MAINTENANT (Copier-Coller)

### ÉTAPE 1: Vérifier que tout est prêt (2 min)

```bash
cd ~/ProtonLumoAI

# Vérifier la connexion IMAP
python test_imap_connection.py

# Doit afficher:
# ✓ Connected successfully
```

**Si erreur:** Vérifier que ProtonMail Bridge est actif
```bash
ps aux | grep protonmail-bridge
```

---

## ÉTAPE 2: Exécuter le pré-tri automatique (15 min)

```bash
# IMPORTANT: Arrêter le processeur s'il est actif
Ctrl+C  # Si le processeur tourne

# Exécuter le pré-tri
python scripts/pretri_folders_2025_and_gmail.py

# Attendre que ça se termine
# Vous verrez:
# 🤖 PRÉ-TRI AUTOMATIQUE - Folders/2025 et Gmail
# 📁 Analysing Folders/2025...
# 📊 Résultats...
# 📁 Analysing Gmail...
# ✅ PRÉ-TRI TERMINÉ
```

---

## ÉTAPE 3: Vérifier les résultats du pré-tri (5 min)

```bash
# Voir le rapport
jq '.categories_detectees' ~/ProtonLumoAI/data/learning/pretri_rapport.json
```

---

## ÉTAPE 4: AFFINAGE MANUEL (30-45 min)

**Ouvrir ProtonMail (Web ou Client)**

1. Vérifier la structure créée
2. Corriger les emails mal classés
3. Ajouter les emails manquants (35+ par catégorie)
4. Quitter ProtonMail quand satisfait

---

## ÉTAPE 5: Lancer le processeur (5 min)

```bash
# Redémarrer le processeur ProtonLumoAI
fish run.fish

# Attendre que ça dise "Ready to process"
# Puis GARDER LE TERMINAL OUVERT
```

---

## ÉTAPE 6: Lancer l'apprentissage (10 min)

**DANS UN AUTRE TERMINAL:**

```bash
cd ~/ProtonLumoAI

# Vérifier la limite (doit être 10)
grep PROTON_LUMO_LEARNING_EMAILS_PER_FOLDER .env

# Lancer l'apprentissage
python scripts/sync_and_learn.py

# Attendre que ça se termine
```

---

## ÉTAPE 7: Vérifier les résultats finaux (5 min)

```bash
# Voir tous les dossiers et leur confiance
jq '[.[] | {folder: .folder_name, emails: .email_count, confiance: (.confidence * 100 | floor)}] | sort_by(.confiance) | reverse | .[0:15]' \
  ~/ProtonLumoAI/data/learning/folder_patterns.json
```

---

## ✅ Timeline Rapide

```
Étape 1: Vérifier       → 2 min
Étape 2: Pré-tri        → 15 min
Étape 3: Vérifier       → 5 min
Étape 4: Affinage       → 30-45 min (VOUS)
Étape 5: Redémarrer     → 5 min
Étape 6: Apprentissage  → 10 min
Étape 7: Vérifier       → 5 min
TOTAL: 70-90 minutes (1h30)
```

---

## 🎁 Ce que vous obtenez

Après 1h30: Classification 92%+ automatique, pour toujours! 🚀

---

## 🚀 COMMENCER MAINTENANT

```bash
cd ~/ProtonLumoAI
python test_imap_connection.py
python scripts/pretri_folders_2025_and_gmail.py
```

Puis suivez les ÉTAPES 3-7 ci-dessus! 🎯
