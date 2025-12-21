# Déploiement du site sur Dokploy

## Configuration

1. **Modifier l'URL du bot** dans `index.html` (ligne ~518) :
   ```javascript
   const BOT_URL = 'https://VOTRE-URL-BOT-DOKPLOY.com';
   ```
   Remplacez par l'URL de votre application bot sur Dokploy.

## Déploiement sur Dokploy

### 1. Créer une nouvelle application
- Dans Dokploy, créez une **nouvelle application**
- Nommez-la par exemple : `psm-bot-site` ou `psg-pmr-site`

### 2. Connecter le dépôt GitHub
- Sélectionnez le même dépôt : `facecacher/psg-pmr-bot`
- **Important** : Dans les paramètres, configurez le **"Root Directory"** ou **"Build Context"** à : `Site/`
- Cela indique à Dokploy de construire uniquement le dossier `Site/`

### 3. Configuration
- **Build Type** : `Docker` ou `Dockerfile`
- **Port** : `8080`
- **Root Directory** : `Site/` (très important !)

### 4. Déployer
- Cliquez sur "Deploy"
- Une fois déployé, Dokploy vous donnera une URL publique pour le site

### 5. Configurer un domaine personnalisé (optionnel)
- Dans les paramètres de l'application site
- Ajoutez votre domaine personnalisé
- Configurez les DNS selon les instructions Dokploy

## Architecture finale

- **Application 1 (Bot)** : `https://bot.dokploy.com` → Génère `status.json`
- **Application 2 (Site)** : `https://site.dokploy.com` → Affiche le site et lit `status.json` depuis le bot
