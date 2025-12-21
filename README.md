# PSM Bot

Bot de surveillance des places PMR (Personnes à Mobilité Réduite) pour les matchs du PSG.

## Configuration

Variables d'environnement (optionnelles, valeurs par défaut dans le code) :

- `TELEGRAM_TOKEN` : Token du bot Telegram
- `TELEGRAM_CHAT_ID` : ID du chat Telegram pour les notifications

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
5. Déployer

Le bot utilise le mode headless avec les arguments nécessaires pour fonctionner dans un container Docker.

