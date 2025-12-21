# PSM Bot

Bot de surveillance des places PMR (Personnes à Mobilité Réduite) pour les matchs du PSG.

## Configuration

Variables d'environnement requises :

- `TELEGRAM_TOKEN` : Token du bot Telegram
- `TELEGRAM_CHAT_ID` : ID du chat Telegram pour les notifications

Variables d'environnement optionnelles :

- `HEADLESS` : Mode headless du navigateur (par défaut: `true`). Mettre à `false` pour voir le navigateur (utile pour les tests locaux)

## Déploiement avec Docker

```bash
docker build -t psm-bot .
docker run -e TELEGRAM_TOKEN="votre_token" -e TELEGRAM_CHAT_ID="votre_chat_id" psm-bot
```

## Déploiement sur Dokploy

1. Pousser le code sur GitHub
2. Dans Dokploy, créer une nouvelle application
3. Connecter le dépôt GitHub
4. Configurer les variables d'environnement :
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Déployer

