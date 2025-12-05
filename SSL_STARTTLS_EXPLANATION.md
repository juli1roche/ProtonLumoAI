# Explication : Correction SSL/STARTTLS pour ProtonMail Bridge

## Problème identifié

ProtonMail Bridge n'utilise **pas SSL/TLS direct** sur le port 1143. Il utilise **STARTTLS**, qui est un protocole différent :

- **SSL/TLS direct** : Connexion chiffrée dès le départ (port 465, 993)
- **STARTTLS** : Connexion en clair d'abord, puis upgrade vers TLS (port 143, 1143)

## Erreur initiale

```
[SSL] record layer failure (_ssl.c:1032)
```

Cette erreur survient quand on essaie de faire une connexion SSL/TLS directe sur un port STARTTLS.

## Solution implémentée

### Avant (incorrect)

```python
mailbox = MailBox(IMAP_HOST, IMAP_PORT, ssl_context=ssl_context)
mailbox.login(IMAP_USERNAME, IMAP_PASSWORD)
```

### Après (correct)

```python
# ProtonMail Bridge utilise STARTTLS (pas SSL direct)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Utiliser ssl=False pour STARTTLS
mailbox = MailBox(IMAP_HOST, IMAP_PORT, ssl=False)
mailbox.starttls(ssl_context=ssl_context)
mailbox.login(IMAP_USERNAME, IMAP_PASSWORD)
```

## Étapes de la connexion

1. **Connexion non chiffrée** : `MailBox(IMAP_HOST, IMAP_PORT, ssl=False)`
   - Établit une connexion TCP simple au port 1143

2. **Upgrade STARTTLS** : `mailbox.starttls(ssl_context=ssl_context)`
   - Demande au serveur d'upgrader la connexion vers TLS
   - Le serveur utilise un certificat auto-signé (d'où `CERT_NONE`)

3. **Authentification** : `mailbox.login(IMAP_USERNAME, IMAP_PASSWORD)`
   - Maintenant que la connexion est chiffrée, envoyer les identifiants

## Vérification

Un script de test `test_imap_starttls.py` a été créé pour vérifier la connexion :

```bash
python3 test_imap_starttls.py
```

Résultat :
```
✓ SUCCÈS ! Connexion IMAP STARTTLS fonctionnelle
```

## Références

- [RFC 3501 - IMAP4rev1](https://tools.ietf.org/html/rfc3501)
- [RFC 3207 - STARTTLS Extension](https://tools.ietf.org/html/rfc3207)
- [ProtonMail Bridge Documentation](https://proton.me/support/proton-mail-bridge)
