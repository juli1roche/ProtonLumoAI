# Configuration de ProtonMail Bridge

Ce guide vous aide à configurer ProtonMail Bridge pour ProtonLumoAI.

## 🔧 Prérequis

- ProtonMail Bridge installé : `/usr/local/bin/proton-bridge`
- Compte ProtonMail actif
- Fichier `.env` configuré avec vos identifiants

## 📋 Étapes de configuration

### Étape 1 : Vérifier l'installation

```bash
proton-bridge --help
```

Si vous voyez l'aide de ProtonMail Bridge, c'est bon !

### Étape 2 : Lancer ProtonMail Bridge

**Option A : Mode gRPC (Recommandé pour automatisation)**

```bash
proton-bridge --grpc --noninteractive &
```

**Option B : Mode interface graphique**

```bash
flatpak run ch.protonmail.protonmail-bridge
```

### Étape 3 : Ajouter votre compte

#### Via l'interface graphique (Option B)

1. Ouvrez l'interface ProtonMail Bridge
2. Cliquez sur **"Add Account"** ou **"Ajouter un compte"**
3. Entrez votre email ProtonMail
4. Entrez votre mot de passe ProtonMail
5. Attendez la configuration
6. Notez le **mot de passe IMAP** généré

#### Via la ligne de commande (Option A)

Si vous utilisez le mode gRPC, ProtonMail Bridge stocke les comptes dans :
```
~/.config/protonmail/bridge-v3/
```

Les fichiers de configuration seront créés automatiquement après la première connexion.

### Étape 4 : Mettre à jour le fichier .env

Une fois que vous avez le mot de passe IMAP, mettez à jour votre fichier `.env` :

```bash
nano ~/.ProtonLumoAI/.env
```

Remplacez la ligne :
```
PROTON_PASSWORD=votre_ancien_mot_de_passe
```

par :
```
PROTON_PASSWORD=votre_mot_de_passe_IMAP_genere
```

### Étape 5 : Tester la connexion

```bash
cd ~/ProtonLumoAI
source venv/bin/activate.fish
source scripts/load_env.fish
python3 scripts/email_processor.py
```

Vous devriez voir les logs de connexion à ProtonMail Bridge.

## 🔍 Dépannage

### Erreur : "Connection refused"

ProtonMail Bridge n'est pas en cours d'exécution. Lancez-le :

```bash
proton-bridge --grpc --noninteractive &
```

### Erreur : "Authentication failed"

Le mot de passe IMAP est incorrect. Vérifiez que vous avez copié le bon mot de passe depuis ProtonMail Bridge.

### ProtonMail Bridge ne démarre pas

Vérifiez que le binaire est exécutable :

```bash
ls -la /usr/local/bin/proton-bridge
```

Si ce n'est pas exécutable :

```bash
sudo chmod +x /usr/local/bin/proton-bridge
```

## 📁 Fichiers de configuration

ProtonMail Bridge stocke sa configuration dans :

```
~/.config/protonmail/bridge-v3/
```

Les fichiers importants :

- `grpcServerConfig.json` - Configuration du serveur gRPC
- `insecure/` - Données sensibles (chiffrées)

## 🔐 Sécurité

- **Ne partagez jamais** votre mot de passe IMAP
- **Ne commitez jamais** votre fichier `.env` avec les identifiants
- Utilisez un mot de passe fort pour votre compte ProtonMail

## 📞 Support

Pour plus d'informations sur ProtonMail Bridge :
- [Documentation officielle](https://proton.me/support/mail-bridge)
- [GitHub ProtonMail Bridge](https://github.com/ProtonMail/proton-bridge)
