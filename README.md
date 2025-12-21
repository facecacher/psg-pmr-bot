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

### Prérequis
- ✅ Code poussé sur GitHub (déjà fait : `facecacher/psg-pmr-bot`)
- ✅ Compte Dokploy configuré
- ✅ Accès à votre token Telegram et Chat ID

### Étapes détaillées

#### 1. Créer une nouvelle application dans Dokploy
- Connectez-vous à votre instance Dokploy
- Cliquez sur **"New Application"** ou **"Créer une application"**
- Choisissez **"GitHub"** comme source

#### 2. Connecter le dépôt GitHub
- Dokploy vous demandera de vous connecter à GitHub (si ce n'est pas déjà fait)
- Autorisez Dokploy à accéder à vos dépôts
- Sélectionnez le dépôt : `facecacher/psg-pmr-bot`
- Choisissez la branche : `main` (ou `master`)

#### 3. Configuration de l'application
Dokploy devrait détecter automatiquement que c'est une application Docker grâce au `Dockerfile`.

**Paramètres importants :**
- **Build Pack** : Docker (automatiquement détecté)
- **Port** : Pas nécessaire (c'est un bot, pas un serveur web)
- **Root Directory** : `/` (par défaut)

#### 4. Configurer les variables d'environnement
Dans la section **"Environment Variables"** ou **"Variables d'environnement"**, ajoutez :

| Variable | Valeur | Description |
|----------|--------|-------------|
| `TELEGRAM_TOKEN` | `8222793392:AAFBtlCNAlPyUYgf1aup06HAvRO9V14DmRo` | Token de votre bot Telegram |
| `TELEGRAM_CHAT_ID` | `-1003428870741` | ID du chat pour les notifications |
| `HEADLESS` | `true` | Mode headless (optionnel, `true` par défaut) |

**⚠️ Important :** Remplacez les valeurs ci-dessus par vos vraies valeurs (ne partagez jamais vos tokens publiquement).

#### 5. Déployer
- Cliquez sur **"Deploy"** ou **"Déployer"**
- Dokploy va :
  1. Cloner le code depuis GitHub
  2. Construire l'image Docker (cela peut prendre 5-10 minutes la première fois)
  3. Installer les dépendances Python (playwright, requests)
  4. Installer Chromium pour Playwright
  5. Lancer le bot

#### 6. Vérifier le déploiement
- Allez dans l'onglet **"Logs"** pour voir les logs en temps réel
- Vous devriez voir des messages comme :
  ```
  PSG vs PARIS FC → PMR trouvées : 0
  ⏳ Pause 92 secondes...
  ```
- Le bot devrait commencer à surveiller les matchs automatiquement

### Dépannage

**Le bot ne démarre pas :**
- Vérifiez les logs dans Dokploy
- Assurez-vous que les variables d'environnement sont bien configurées
- Vérifiez que le token Telegram est valide

**Erreur "Playwright browser not found" :**
- Le Dockerfile installe déjà Chromium, mais si ça échoue, vérifiez les logs de build

**Le bot ne détecte pas les places :**
- Vérifiez que le site de la billetterie PSG est accessible
- Regardez les logs pour voir les erreurs éventuelles
- Essayez de mettre `HEADLESS=false` temporairement pour debug (si Dokploy supporte l'affichage)

### Mise à jour du code
Quand vous modifiez le code :
1. Poussez les changements sur GitHub : `git push`
2. Dans Dokploy, cliquez sur **"Redeploy"** ou **"Redéployer"**
3. Dokploy reconstruira l'image et redémarrera le bot

