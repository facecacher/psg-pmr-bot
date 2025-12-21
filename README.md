# PSM Bot

Bot de surveillance des places PMR (Personnes à Mobilité Réduite) pour les matchs du PSG avec interface web en temps réel.

## Fonctionnalités

- ✅ Surveillance automatique des places PMR pour plusieurs matchs
- ✅ Notifications Telegram en temps réel
- ✅ Interface web avec mise à jour automatique toutes les 10 secondes
- ✅ Génération de `status.json` pour le site web

## Configuration

Variables d'environnement (optionnelles, valeurs par défaut dans le code) :

- `TELEGRAM_TOKEN` : Token du bot Telegram
- `TELEGRAM_CHAT_ID` : ID du chat Telegram pour les notifications

## Structure du projet

```
psm-bot/
├── psm.py              # Script principal du bot
├── Site/
│   └── index.html      # Interface web
├── status.json         # Fichier généré par le bot (non versionné)
├── Dockerfile         # Configuration Docker
└── requirements.txt    # Dépendances Python
```

## Déploiement avec Docker

```bash
docker build -t psm-bot .
docker run -e TELEGRAM_TOKEN="votre_token" -e TELEGRAM_CHAT_ID="votre_chat_id" psm-bot
```

## Déploiement sur Dokploy

1. Pousser le code sur GitHub
2. Dans Dokploy, créer une nouvelle application
3. Connecter le dépôt GitHub
4. Configurer les variables d'environnement dans **"Environment Settings"** (pas Build-time) :
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Configurer le port si nécessaire (le bot génère `status.json` mais ne sert pas de site web par défaut)
6. Déployer

## Interface web

Le fichier `Site/index.html` lit automatiquement `status.json` toutes les 10 secondes pour afficher les données en temps réel.

Pour servir le site web, vous pouvez :
- Héberger `Site/index.html` sur un service gratuit (Netlify, Vercel, GitHub Pages)
- Ou ajouter un serveur web simple dans `psm.py`

Le bot utilise le mode headless avec les arguments nécessaires pour fonctionner dans un container Docker.

