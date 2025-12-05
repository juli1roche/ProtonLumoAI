# Guide d'Installation de ProtonLumoAI

Ce guide vous aidera à installer et à configurer ProtonLumoAI sur votre système.

## Prérequis

- Python 3.10+
- `pip` et `venv`
- Git
- ProtonMail Bridge installé et configuré

## Installation Rapide (5 minutes)

1.  **Clonez le repository** :

    ```bash
    git clone https://github.com/juli1roche/ProtonLumoAI.git
    cd ProtonLumoAI
    ```

2.  **Configurez vos identifiants** :

    ```bash
    cp .env.example .env
    nano .env # Éditez ce fichier avec vos informations ProtonMail
    ```

3.  **Lancez le script d'installation** :

    Ce script va créer un environnement virtuel, installer les dépendances et lancer le processeur.

    ```bash
    # Pour les utilisateurs de Bash/Zsh
    bash run.sh

    # Pour les utilisateurs de Fish
    fish run.fish
    ```

## Vérification de l'Installation

Après avoir lancé le script, vous devriez voir des logs indiquant que le processeur a démarré et tente de se connecter à ProtonMail Bridge.

```
✓ Configuration chargée
🚀 Démarrage du processeur d'emails...
INFO | Connexion à 127.0.0.1:1143...
SUCCESS | Connexion établie
```

## Lancer en tant que Service (Linux avec systemd)

Pour que le script tourne en continu en arrière-plan, vous pouvez l'installer en tant que service `systemd`.

1.  **Éditez le script d'installation du service** pour vous assurer que le nom d'utilisateur (`USER_NAME`) correspond bien au vôtre.

    ```bash
    nano install_service.sh
    ```

2.  **Exécutez le script d'installation** :

    ```bash
    sudo bash install_service.sh
    ```

3.  **Vérifiez le statut du service** :

    ```bash
    sudo systemctl status protonlumoai.service
    ```

## Dépannage

-   **`ModuleNotFoundError`** : Assurez-vous que vous avez bien lancé le script `run.sh` ou `run.fish` qui installe les dépendances dans un environnement virtuel.
-   **Erreur de connexion SSL** : Vérifiez que ProtonMail Bridge est bien en cours d'exécution et que les informations dans votre fichier `.env` sont correctes.

