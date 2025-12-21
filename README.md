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

### ✅ Code déjà sur GitHub
Le code est disponible sur : `https://github.com/facecacher/psg-pmr-bot`

### 📋 Guide étape par étape pour Dokploy

#### 1. Créer une nouvelle application
- Connectez-vous à votre instance Dokploy
- Cliquez sur **"New Application"** ou **"Nouvelle application"**
- Choisissez **"GitHub"** comme source

#### 2. Connecter le dépôt GitHub
- Si c'est la première fois, connectez votre compte GitHub
- Autorisez Dokploy à accéder à vos dépôts
- Sélectionnez le dépôt : **`facecacher/psg-pmr-bot`**
- Choisissez la branche : **`main`**

#### 3. Configuration de l'application
- **Build Type** : Sélectionnez **"Docker"** ou **"Dockerfile"**
  - Dokploy devrait détecter automatiquement le Dockerfile
- **Port** : Configurez le port **`8080`**
  - Le bot sert maintenant le site web (`index.html`) et `status.json` sur ce port

#### 4. ⚠️ IMPORTANT : Configurer les variables d'environnement
Dans la section **"Environment Settings"** (PAS "Build-time Arguments" ni "Build-time Secrets"), ajoutez :

**Variable 1 :**
- **Nom** : `TELEGRAM_TOKEN`
- **Valeur** : `8222793392:AAFBtlCNAlPyUYgf1aup06HAvRO9V14DmRo`
- Cliquez sur **"Add"**

**Variable 2 :**
- **Nom** : `TELEGRAM_CHAT_ID`
- **Valeur** : `-1003428870741`
- Cliquez sur **"Add"`

⚠️ **CRITIQUE** : Ces variables DOIVENT être dans **"Environment Settings"** (runtime), pas dans "Build-time Arguments" !

#### 5. Déployer
- Cliquez sur **"Deploy"** ou **"Déployer"**
- Le build peut prendre 5-10 minutes la première fois
- Vous verrez les logs de construction dans l'onglet **"Build Logs"**

#### 6. Vérifier que ça fonctionne
- Allez dans l'onglet **"Logs"** ou **"Runtime Logs"**
- Vous devriez voir :
  ```
  🌐 Serveur web démarré sur le port 8080
  📱 Site accessible sur http://localhost:8080/index.html
  🚀 Bot PSM démarré avec serveur web intégré!
  PSG vs PARIS FC → PMR trouvées : 0
  ⏳ Pause 92 secondes...
  ```
- Le bot vérifie les matchs toutes les ~90 secondes

#### 7. Accéder au site web
- Une fois déployé, Dokploy vous donnera une URL publique
- Accédez à votre site via cette URL (ex: `https://votre-app.dokploy.com`)
- Le site affiche les données en temps réel et se met à jour toutes les 10 secondes

### 📱 Messages Telegram configurés

Le bot envoie automatiquement des messages Telegram avec le format suivant :

**Quand des places PMR sont disponibles :**
```
🔥 ALERTE PLACE PMR DISPONIBLE ! 🔥

🎟️ Match : {nom}
✅ Places PMR trouvées !

👉 Fonce sur la billetterie maintenant !
```

**Quand aucune place n'est disponible (toutes les 8h) :**
```
😴 Pas encore de places PMR...

🎟️ Match : {nom}
❌ Aucune place PMR disponible pour le moment

💪 On continue de surveiller pour toi !
```

### 🔧 Fonctionnalités incluses

- ✅ Mode headless activé (fonctionne sans écran sur Docker)
- ✅ Arguments Chrome optimisés pour éviter la détection
- ✅ Scroll progressif pour un comportement plus naturel
- ✅ Génération de `status.json` pour l'interface web
- ✅ Variables d'environnement pour la sécurité
- ✅ Cooldown de 8h pour éviter le spam Telegram

## Interface web

Le bot inclut maintenant un **serveur web intégré** qui :
- ✅ Sert `Site/index.html` sur le port 8080
- ✅ Sert `status.json` pour les données en temps réel
- ✅ Met à jour automatiquement toutes les 10 secondes
- ✅ Fonctionne directement sur Dokploy

**Accès au site :**
- Une fois déployé sur Dokploy, utilisez l'URL publique fournie
- Le site est accessible directement via cette URL
- Les données se mettent à jour automatiquement toutes les 10 secondes

Le bot utilise le mode headless avec les arguments nécessaires pour fonctionner dans un container Docker.

