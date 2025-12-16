# 🚀 ProtonLumoAI - Guide des Optimisations

**Réduction des coûts API et amélioration des performances**

Date: 16 décembre 2025

---

## 🎯 Objectifs

- **Réduire les coûts API de 60-80%**
- **Accélérer le traitement** (10x plus rapide sur gros volumes)
- **Automatiser complètement** après phase d'apprentissage
- **Respecter les limites** de taux de l'API Perplexity

---

## ✨ Nouvelles Fonctionnalités

### 1. 💾 Cache Intelligent

**Principe**: Ne jamais classifier deux fois le même type d'email

```python
from scripts.email_classifier_optimized import EmailClassifierOptimized

classifier = EmailClassifierOptimized()

# Premier email de amazon.com
result1 = classifier.classify("1", "Votre commande", "...", "noreply@amazon.com")
# Méthode: "batch_api" ou "keyword"

# Deuxième email similaire de amazon.com
result2 = classifier.classify("2", "Expédition commande", "...", "noreply@amazon.com")
# Méthode: "cached" → Gratuit, instantané!
```

**Résultats attendus**:
- 📈 **Cache hit rate: 40-60%** après 1 semaine
- 📈 **Cache hit rate: 70-85%** après 1 mois

### 2. 📦 Batch Processing

**Principe**: Classifier 10-20 emails en un seul appel API

**Avant** (coûteux):
```python
# 100 emails = 100 appels API = $0.50
for email in emails:
    result = classifier.classify(email)
```

**Après** (optimisé):
```python
# 100 emails = 5-10 appels API = $0.05
results = classifier.classify_batch(emails)
```

**📉 Réduction des coûts: -80% minimum**

### 3. ⏱️ Rate Limiter

**Principe**: Respecter les limites de l'API (50 appels/minute)

```python
# Configurable selon votre plan Perplexity
classifier = EmailClassifierOptimized()
classifier.rate_limiter = RateLimiter(max_calls=50, period=60)

# Attente automatique si limite atteinte
results = classifier.classify_batch(large_email_list)  # ✅ Sécurisé
```

### 4. 📤 Export Filtres ProtonMail

**Principe**: Une fois l'apprentissage terminé, utiliser des règles ProtonMail natives (0 coût)

```python
classifier = EmailClassifierOptimized()

# Après 2-4 semaines d'utilisation
sieve_rules = classifier.export_to_protonmail_filters(min_occurrences=5)

print(sieve_rules)
```

**Exemple de sortie** (`protonmail_filters.sieve`):
```sieve
# ProtonLumoAI - Règles automatiques générées
# Date: 2025-12-16T10:45:00

# Règle pour amazon.com -> VENTE (47 emails)
if header :contains "From" "amazon.com" {
    fileinto "Folders/Achats";
    stop;
}

# Règle pour credit.fr -> BANQUE (23 emails)
if header :contains "From" "credit.fr" {
    fileinto "Folders/Administratif/Banque";
    stop;
}
```

**🔧 Installation dans ProtonMail Bridge**:
```bash
# Copier les règles dans la config ProtonMail Bridge
cp ~/ProtonLumoAI/config/protonmail_filters.sieve ~/.config/protonmail/bridge/

# Redémarrer le bridge
sudo systemctl restart protonmail-bridge
```

---

## 📊 Métriques et Surveillance

### Afficher les statistiques

```python
classifier = EmailClassifierOptimized()

# Traiter des emails...
results = classifier.classify_batch(emails)

# Afficher les métriques
metrics = classifier.get_metrics()
print(json.dumps(metrics, indent=2))
```

**Exemple de sortie**:
```json
{
  "total_classifications": 1250,
  "api_calls": 45,
  "batch_calls": 12,
  "cache_hits": 680,
  "keyword_fallbacks": 525,
  "cache_size_entries": 342,
  "cache_size_mb": 0.84,
  "estimated_cost_usd": 0.225,
  "cost_savings_percent": 96.4
}
```

### Interprétation

- **cost_savings_percent: 96.4%** → 🎉 Excellent! Vous économisez 96% des coûts
- **cache_hits: 680** → 54% des emails sont servis depuis le cache (gratuit)
- **keyword_fallbacks: 525** → 42% classifiés par mots-clés (gratuit)
- **api_calls: 45** → Seulement 3.6% nécessitent l'API payante

---

## 🔄 Migration depuis la Version Standard

### Étape 1: Installer la version optimisée

```bash
cd ~/ProtonLumoAI
git pull origin main

# Vérifier que le nouveau fichier existe
ls -lh scripts/email_classifier_optimized.py
```

### Étape 2: Modifier votre code existant

**Avant**:
```python
from scripts.email_classifier import EmailClassifier

classifier = EmailClassifier()
result = classifier.classify(email_id, subject, body)
```

**Après**:
```python
from scripts.email_classifier_optimized import EmailClassifierOptimized

classifier = EmailClassifierOptimized()

# Mode batch (recommandé)
results = classifier.classify_batch([
    {'email_id': '1', 'subject': 'Test', 'body': '...', 'from': 'sender@example.com'},
    # ... autres emails
])

# OU mode unique (compatible)
result = classifier.classify(email_id, subject, body, from_address)
```

### Étape 3: Activer le cache

```bash
# Le cache est automatique, mais vérifiez la création des dossiers
mkdir -p ~/ProtonLumoAI/data/cache

# Lancer le classifier
python scripts/email_classifier_optimized.py
```

### Étape 4: Générer les filtres ProtonMail (après 2-4 semaines)

```python
from scripts.email_classifier_optimized import EmailClassifierOptimized

classifier = EmailClassifierOptimized()
classifier.export_to_protonmail_filters(min_occurrences=5)

print("✅ Filtres exportés vers ~/ProtonLumoAI/config/protonmail_filters.sieve")
```

---

## 📈 Stratégie d'Optimisation sur 3 Phases

### Phase 1: Apprentissage Intensif (Semaines 1-2)

**Objectif**: Construire le cache rapidement

```python
classifier = EmailClassifierOptimized(use_api=True)

# Traiter TOUS les emails anciens en batch
old_emails = fetch_emails_from_2024_2025()  # 1000+ emails
results = classifier.classify_batch(old_emails)

classifier.save_state()
```

**Coût estimé**: $2-5 pour 1000 emails (en batch)

### Phase 2: Consolidation (Semaines 3-4)

**Objectif**: Affiner les patterns et générer les règles ProtonMail

```python
# Corriger manuellement les erreurs
for result in results:
    if result.confidence < 0.6:
        # Inspecter manuellement
        print(f"Vérifier: {result.subject} -> {result.category}")

# Exporter les règles
classifier.export_to_protonmail_filters(min_occurrences=3)
```

**Coût estimé**: $0.50-1/semaine (cache hit rate ~60%)

### Phase 3: Maintenance (Mois 2+)

**Objectif**: Coût minimal, automatisation maximale

- **80% des emails**: Filtres ProtonMail natifs (gratuit)
- **15% des emails**: Cache (gratuit)
- **5% des emails**: API (nouveaux patterns)

**Coût estimé**: $0.10-0.30/mois

---

## ⚠️ Bonnes Pratiques

### 1. Ne pas gaspiller l'API

❌ **Mauvais**:
```python
# Classifier un email à chaque lecture
for _ in range(10):
    result = classifier.classify(same_email)  # 10 appels API!
```

✅ **Bon**:
```python
# Le cache fait le travail
result1 = classifier.classify(email)  # Appel API
result2 = classifier.classify(email)  # Cache (gratuit)
```

### 2. Privilégier le batch

❌ **Mauvais**:
```python
for email in emails:
    classifier.classify(email['id'], email['subject'], email['body'])
# 100 emails = 100 appels API séparés
```

✅ **Bon**:
```python
classifier.classify_batch(emails)
# 100 emails = 5-10 appels API batchés
```

### 3. Sauvegarder régulièrement le cache

```python
import signal

def save_on_exit(signum, frame):
    classifier.save_state()
    logger.info("💾 Cache sauvegardé avant arrêt")
    exit(0)

signal.signal(signal.SIGINT, save_on_exit)
signal.signal(signal.SIGTERM, save_on_exit)

# Votre code...
try:
    while True:
        process_emails()
        classifier.save_state()  # Sauvegarde périodique
        time.sleep(3600)
except KeyboardInterrupt:
    classifier.save_state()
```

### 4. Nettoyer le cache ancien

```python
# Supprimer les entrées non utilisées depuis 90 jours
from datetime import datetime, timedelta

expiry_date = (datetime.now() - timedelta(days=90)).isoformat()

for key, pattern in list(classifier.cache.items()):
    if pattern.last_used < expiry_date:
        del classifier.cache[key]

classifier.save_state()
logger.info(f"🧹 Cache nettoyé: {len(classifier.cache)} entrées restantes")
```

---

## 🔍 Dépannage

### "Rate limit exceeded"

**Cause**: Trop d'appels API trop rapidement

**Solution**:
```python
# Augmenter la période ou réduire le max
classifier.rate_limiter = RateLimiter(max_calls=30, period=60)
```

### "Cache trop volumineux"

**Cause**: Des milliers d'entrées accumulées

**Solution**:
```bash
# Nettoyer le cache ancien (voir section Bonnes Pratiques)
python -c "
from scripts.email_classifier_optimized import EmailClassifierOptimized
from datetime import datetime, timedelta

c = EmailClassifierOptimized()
expiry = (datetime.now() - timedelta(days=60)).isoformat()
c.cache = {k: v for k, v in c.cache.items() if v.last_used > expiry}
c.save_state()
print(f'✅ Cache réduit à {len(c.cache)} entrées')
"
```

### "Filtres ProtonMail ne fonctionnent pas"

**Causes possibles**:
1. Mauvais emplacement du fichier `.sieve`
2. Syntaxe SIEVE invalide
3. ProtonMail Bridge non redémarré

**Solution**:
```bash
# Vérifier la syntaxe
sievec ~/ProtonLumoAI/config/protonmail_filters.sieve

# Redémarrer le bridge
sudo systemctl restart protonmail-bridge

# Vérifier les logs
journalctl -u protonmail-bridge -f
```

---

## 📊 Comparaison des Versions

| Fonctionnalité | Version Standard | Version Optimisée | Gain |
|-----------------|------------------|-------------------|------|
| **Classification** | 1 email/appel | 10-20 emails/appel | **10-20x** |
| **Cache** | ❌ Non | ✅ Oui | **40-70% gratuit** |
| **Rate Limiting** | ❌ Non | ✅ Oui | **Sécurisé** |
| **Export Filtres** | ❌ Non | ✅ Oui | **80% auto** |
| **Métriques** | ❌ Non | ✅ Oui | **Visibilité** |
| **Coût/1000 emails** | $5-10 | $0.50-1 | **-80 à -95%** |

---

## 🎓 Exemple Complet

```python
#!/usr/bin/env python3
from scripts.email_classifier_optimized import EmailClassifierOptimized
import imaplib
import email
from email.header import decode_header

def main():
    # Initialiser le classifier
    classifier = EmailClassifierOptimized()
    
    # Connexion IMAP (ProtonMail Bridge)
    mail = imaplib.IMAP4('127.0.0.1', 1143)
    mail.starttls()
    mail.login(os.getenv('PROTON_USERNAME'), os.getenv('PROTON_PASSWORD'))
    mail.select('INBOX')
    
    # Récupérer les emails non lus
    _, message_numbers = mail.search(None, 'UNSEEN')
    
    emails_to_classify = []
    for num in message_numbers[0].split()[:50]:  # Max 50 à la fois
        _, msg_data = mail.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        
        subject = decode_header(msg['Subject'])[0][0]
        from_addr = msg.get('From', '')
        body = get_email_body(msg)
        
        emails_to_classify.append({
            'email_id': num.decode(),
            'subject': subject,
            'body': body,
            'from': from_addr
        })
    
    # Classification batch
    results = classifier.classify_batch(emails_to_classify)
    
    # Déplacer les emails
    for result in results:
        if result.confidence >= 0.6:
            folder = classifier.categories[result.category].folder
            mail.copy(result.email_id, folder)
            mail.store(result.email_id, '+FLAGS', '\\Deleted')
            print(f"✓ {result.subject[:40]} -> {folder} ({result.method})")
    
    mail.expunge()
    mail.logout()
    
    # Afficher les métriques
    print("\n📊 Métriques:")
    print(json.dumps(classifier.get_metrics(), indent=2))
    
    # Sauvegarder l'état
    classifier.save_state()

if __name__ == '__main__':
    main()
```

---

## 🚀 Prochaines Étapes

1. ✅ **Migrer vers la version optimisée**
2. ✅ **Lancer l'apprentissage sur emails anciens** (Phase 1)
3. ✅ **Surveiller les métriques** pendant 2 semaines
4. ✅ **Générer les filtres ProtonMail** (Phase 2)
5. ✅ **Automatiser complètement** (Phase 3)

**Objectif final**: **$0.10-0.30/mois au lieu de $10-20/mois** 🎉

---

## 📝 Ressources

- **Code source**: `scripts/email_classifier_optimized.py`
- **Documentation API Perplexity**: [docs.perplexity.ai](https://docs.perplexity.ai)
- **Filtres SIEVE ProtonMail**: [protonmail.com/support/sieve](https://protonmail.com/support/sieve)
- **Issue tracker**: [github.com/juli1roche/ProtonLumoAI/issues](https://github.com/juli1roche/ProtonLumoAI/issues)

---

**Auteur**: Julien Roche  
**Date**: 16 décembre 2025  
**Licence**: MIT
