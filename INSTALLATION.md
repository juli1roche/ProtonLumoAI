# ProtonLumoAI - Guide d'Installation Complet

**Date** : 2025-12-05  
**Status** : ✅ **TESTÉ ET FONCTIONNEL**  
**Shell** : Fish 4.2.1 (CachyOS)  
**Python** : 3.13

---

## 🚀 Installation Rapide (5 minutes)

### 1. Cloner le Repository
```fish
cd ~
git clone https://github.com/juli1roche/ProtonLumoAI.git
cd ProtonLumoAI
```

### 2. Configurer les Credentials
```fish
# Copier l'exemple
cp .env.example .env

# Éditer avec vos credentials ProtonMail
nano .env
```

**Remplir les variables** :
```dotenv
PROTON_BRIDGE_HOST=127.0.0.1
PROTON_BRIDGE_PORT=1143
PROTON_USERNAME=votre_email@pm.me
PROTON_PASSWORD=votre_bridge_password
```

### 3. Créer l'Environnement Virtuel
```fish
python3 -m venv venv
```

### 4. Installer les Dépendances
```fish
./venv/bin/pip install imap-tools loguru pydantic scikit-learn pandas
```

### 5. Lancer le Processeur
```fish
fish run.fish
```

**C'est tout !** 🎉

---

## 📋 Vérification de l'Installation

### Vérifier que loguru est installé
```fish
./venv/bin/python3 -c "import loguru; print('✓ loguru installé')"
```

### Vérifier que tous les modules sont disponibles
```fish
./venv/bin/python3 -c "
import loguru
import imap_tools
import pydantic
import sklearn
import pandas
print('✓ Tous les modules sont installés')
"
```

### Vérifier les jobs en arrière-plan
```fish
jobs
ps aux | grep email_processor
```

### Tuer un processus qui tourne
```fish
# Voir les processus
ps aux | grep email_processor

# Tuer avec le PID
kill -9 <PID>

# Ou tuer tous les email_processor
pkill -f email_processor
```

---

## 🔧 Dépannage

### Erreur : `ModuleNotFoundError: No module named 'loguru'`

**Cause** : Les dépendances ne sont pas installées dans le venv.

**Solution** :
```fish
cd ~/ProtonLumoAI
./venv/bin/pip install imap-tools loguru pydantic scikit-learn pandas
```

### Erreur : `[SSL] record layer failure`

**Cause** : ProtonMail Bridge n'est pas en cours d'exécution.

**Solution** : Démarrez ProtonMail Bridge sur votre machine.

### Erreur : `Connection refused`

**Cause** : ProtonMail Bridge n'est pas accessible sur 127.0.0.1:1143.

**Solution** :
1. Vérifiez que ProtonMail Bridge est en cours d'exécution
2. Vérifiez que le port 1143 est correct dans `.env`
3. Vérifiez que votre VPN ne bloque pas les connexions locales

### Erreur : `Unknown command: deactivate`

**Cause** : Fish shell ne reconnaît pas la commande `deactivate`.

**Solution** : Le script `run.fish` gère cela automatiquement. Assurez-vous d'utiliser la dernière version :
```fish
git pull origin main
```

---

## 📊 Configuration Vérifiée

**ProtonMail Bridge** :
- Host : `127.0.0.1`
- Port : `1143` (STARTTLS)
- Protocol : IMAP4 + STARTTLS
- SMTP Port : `1025`

**Traitement** :
- Poll Interval : 60 secondes
- Auto-Improve : 3600 secondes (1h)
- Unseen Only : true
- Dry-Run : false

**Python** :
- Version : 3.13
- Venv : `./venv`
- Modules : imap-tools, loguru, pydantic, scikit-learn, pandas

---

## 🎯 Utilisation

### Démarrer le processeur
```fish
cd ~/ProtonLumoAI
fish run.fish
```

### Arrêter le processeur
```fish
# Ctrl+C dans le terminal où il tourne
# Ou tuer le processus
pkill -f email_processor
```

### Voir les logs en temps réel
```fish
tail -f logs/processor.log
```

### Vérifier les jobs
```fish
jobs
ps aux | grep email_processor
```

---

## 📝 Fichiers Importants

| Fichier | Description |
|---------|-------------|
| `run.fish` | Script de démarrage principal |
| `.env` | Configuration (credentials) |
| `.env.example` | Exemple de configuration |
| `scripts/email_processor.py` | Processeur principal |
| `scripts/email_classifier.py` | Système de classification |
| `logs/processor.log` | Logs du processeur |

---

## 🔐 Sécurité

- ✅ `.env` avec credentials n'est **PAS** sur GitHub
- ✅ `.env.example` fourni pour guide
- ✅ Pas de hardcoding de credentials
- ✅ Variables d'environnement utilisées correctement

---

## 📞 Support

- **README.md** : Documentation complète
- **CHANGELOG.md** : Historique des changements
- **SSL_STARTTLS_EXPLANATION.md** : Explication technique
- **GitHub Issues** : Pour signaler des problèmes

---

## ✨ Conclusion

ProtonLumoAI est maintenant **prêt pour utilisation** ! 

Suivez les 5 étapes d'installation rapide et vous serez opérationnel en quelques minutes. 🚀
