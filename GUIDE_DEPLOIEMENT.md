# 📘 Guide de Déploiement Complet - Bot PSG PMR avec API Flask

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture du système](#architecture-du-système)
3. [Prérequis](#prérequis)
4. [Configuration GitHub](#configuration-github)
5. [Déploiement sur Dokploy - Application Bot](#déploiement-sur-dokploy---application-bot)
6. [Déploiement sur Dokploy - Application Site](#déploiement-sur-dokploy---application-site)
7. [Configuration des domaines](#configuration-des-domaines)
8. [Vérification et tests](#vérification-et-tests)
9. [Utilisation de l'interface admin](#utilisation-de-linterface-admin)
10. [Dépannage](#dépannage)

---

## 🎯 Vue d'ensemble

Ce projet comprend :
- **Bot Python** (`psm.py`) : Surveille les places PMR pour les matchs PSG
- **API Flask** : Intégrée dans le bot, expose des endpoints REST
- **Site public** (`Site/index.html`) : Interface utilisateur en temps réel
- **Interface admin** (`Site/admin.html`) : Dashboard de gestion

**URLs finales :**
- Bot + API : `https://app.lesbricolesdelekmane.fun`
- Site public : `https://psg.lesbricolesdelekmane.fun`
- Admin : Accessible via le site public

---

## 🏗️ Architecture du système

```
┌─────────────────────────────────────────────────────────────┐
│                    DOKPLOY SERVER                          │
│                                                             │
│  ┌──────────────────────────┐  ┌──────────────────────┐  │
│  │  Application 1 : BOT     │  │  Application 2 : SITE│  │
│  │  Port: 8081, 5000        │  │  Port: 8080           │  │
│  │                           │  │                       │  │
│  │  - psm.py (bot)          │  │  - index.html        │  │
│  │  - API Flask (port 5000) │  │  - admin.html        │  │
│  │  - Serveur web (port 8081)│  │  - Static files      │  │
│  │  - status.json            │  │                       │  │
│  │  - matches.json           │  │                       │  │
│  │  - analytics.json         │  │                       │  │
│  └──────────────────────────┘  └──────────────────────┘  │
│           │                              │                │
│           └──────────┬───────────────────┘                │
│                      │                                     │
│              ┌───────▼────────┐                           │
│              │  Domaines      │                           │
│              │  - app.* (bot) │                           │
│              │  - psg.* (site)│                           │
│              └───────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Prérequis

### 1. Compte GitHub
- ✅ Compte GitHub actif
- ✅ Dépôt : `https://github.com/facecacher/psg-pmr-bot`
- ✅ Code déjà poussé sur la branche `main`

### 2. Compte Dokploy
- ✅ Instance Dokploy accessible
- ✅ Accès administrateur
- ✅ Connexion GitHub configurée

### 3. Domaines (optionnel mais recommandé)
- ✅ `app.lesbricolesdelekmane.fun` → Bot + API
- ✅ `psg.lesbricolesdelekmane.fun` → Site public

### 4. Telegram Bot
- ✅ Token Telegram : `8222793392:AAFBtlCNAlPyUYgf1aup06HAvRO9V14DmRo`
- ✅ Chat ID : `-1003428870741`

---

## 🔧 Configuration GitHub

### Vérifier que tout est poussé

```bash
# Vérifier les fichiers présents
git status

# Vérifier les fichiers importants
ls -la
# Doit contenir :
# - psm.py
# - api.py (optionnel, API intégrée dans psm.py)
# - requirements.txt
# - Dockerfile
# - Site/index.html
# - Site/admin.html
# - Site/Dockerfile
```

### Structure des fichiers

```
psg-pmr-bot/
├── psm.py                 # Bot principal + API Flask intégrée
├── requirements.txt       # Dépendances Python
├── Dockerfile            # Image Docker pour le bot
├── .gitignore            # Fichiers ignorés
├── README.md             # Documentation
├── GUIDE_DEPLOIEMENT.md  # Ce fichier
└── Site/
    ├── index.html        # Site public
    ├── admin.html        # Interface admin
    └── Dockerfile        # Image Docker pour le site
```

---

## 🚀 Déploiement sur Dokploy - Application Bot

### Étape 1 : Créer une nouvelle application

1. **Connectez-vous à Dokploy**
   - Ouvrez votre instance Dokploy
   - Connectez-vous avec vos identifiants

2. **Créer une nouvelle application**
   - Cliquez sur **"New Application"** ou **"Nouvelle application"**
   - Ou cliquez sur le bouton **"+"** en haut à droite

3. **Choisir la source**
   - Sélectionnez **"GitHub"** comme source
   - Si c'est la première fois, connectez votre compte GitHub
   - Autorisez Dokploy à accéder à vos dépôts

### Étape 2 : Sélectionner le dépôt

1. **Sélectionner le dépôt**
   - Cherchez : `facecacher/psg-pmr-bot`
   - Cliquez dessus

2. **Choisir la branche**
   - Branche : **`main`**
   - (ou `master` si c'est votre branche principale)

### Étape 3 : Configuration de l'application

#### 3.1 Informations de base

- **Nom de l'application** : `psg-pmr-bot` (ou `psm-bot`)
- **Description** : `Bot de surveillance places PMR PSG`

#### 3.2 Configuration du build

- **Build Type** : Sélectionnez **"Docker"** ou **"Dockerfile"**
- Dokploy devrait détecter automatiquement le `Dockerfile` à la racine

#### 3.3 Configuration des ports

⚠️ **IMPORTANT** : Configurez **DEUX ports** :

1. **Port principal** : `8081`
   - Utilisé par le serveur web intégré
   - Sert `status.json` et les fichiers statiques

2. **Port secondaire** : `5000`
   - Utilisé par l'API Flask
   - Endpoints : `/api/*`

**Comment configurer dans Dokploy :**
- Dans la section **"Ports"** ou **"Exposed Ports"**
- Ajoutez :
  - Port `8081` (interne) → Port `8081` (externe)
  - Port `5000` (interne) → Port `5000` (externe)

**OU** configurez un reverse proxy :
- Route `/api/*` → Port `5000`
- Route `/*` → Port `8081`

#### 3.4 Variables d'environnement

⚠️ **CRITIQUE** : Ces variables DOIVENT être dans **"Environment Settings"** (runtime), **PAS** dans "Build-time Arguments" !

**Variable 1 :**
- **Nom** : `TELEGRAM_TOKEN`
- **Valeur** : `8222793392:AAFBtlCNAlPyUYgf1aup06HAvRO9V14DmRo`
- **Type** : Environment Variable (runtime)
- Cliquez sur **"Add"**

**Variable 2 :**
- **Nom** : `TELEGRAM_CHAT_ID`
- **Valeur** : `-1003428870741`
- **Type** : Environment Variable (runtime)
- Cliquez sur **"Add"**

**Vérification :**
- Les variables doivent apparaître dans la section **"Environment Settings"**
- **NE PAS** les mettre dans "Build-time Arguments" ou "Build-time Secrets"

#### 3.5 Configuration avancée (optionnel)

- **Root Directory** : Laisser vide (racine du projet)
- **Build Context** : Laisser vide
- **Dockerfile Path** : `Dockerfile` (par défaut)

### Étape 4 : Déployer

1. **Cliquez sur "Deploy"** ou **"Déployer"**
2. **Attendre le build** (5-10 minutes la première fois)
3. **Surveiller les logs** dans l'onglet **"Build Logs"**

**Logs attendus pendant le build :**
```
Step 1/10 : FROM python:3.11-slim
Step 2/10 : RUN apt-get update...
Step 3/10 : COPY requirements.txt
Step 4/10 : RUN pip install...
Step 5/10 : RUN playwright install chromium
Step 6/10 : RUN playwright install-deps chromium
Step 7/10 : COPY psm.py
Step 8/10 : COPY Site/
Step 9/10 : EXPOSE 8081 5000
Step 10/10 : CMD ["python", "-u", "psm.py"]
```

### Étape 5 : Vérifier les logs runtime

Une fois déployé, allez dans l'onglet **"Logs"** ou **"Runtime Logs"**.

**Logs attendus :**
```
💾 status.json sauvegardé dans: /app/status.json
🔌 API Flask démarrée sur le port 5000
🌐 Serveur web démarré sur le port 8081
📱 Site accessible sur http://localhost:8081/index.html
🚀 Bot PSM démarré avec serveur web intégré!
🌐 Chargement de PSG vs PARIS FC...
✅ Page chargée pour PSG vs PARIS FC
⏳ Attente du chargement complet...
📜 Scroll de la page...
PSG vs PARIS FC → PMR trouvées : 0
⏳ Pause 92 secondes...
```

**Si vous voyez des erreurs :**
- Voir la section [Dépannage](#dépannage)

---

## 🌐 Déploiement sur Dokploy - Application Site

### Étape 1 : Créer une nouvelle application

1. **Créer une nouvelle application** (séparée du bot)
   - Cliquez sur **"New Application"**
   - Nom : `psg-pmr-site` (ou `psm-site`)

2. **Sélectionner le même dépôt**
   - Dépôt : `facecacher/psg-pmr-bot`
   - Branche : `main`

### Étape 2 : Configuration spéciale

#### 2.1 Root Directory / Build Context

⚠️ **TRÈS IMPORTANT** : Configurez le **"Root Directory"** ou **"Build Context"** à : `Site/`

**Comment faire :**
- Dans les paramètres de l'application
- Cherchez **"Root Directory"** ou **"Build Context"**
- Entrez : `Site/`
- Cela indique à Dokploy de construire uniquement le dossier `Site/`

#### 2.2 Configuration du build

- **Build Type** : `Docker` ou `Dockerfile`
- **Dockerfile Path** : `Site/Dockerfile` (ou `Dockerfile` si Root Directory est `Site/`)

#### 2.3 Configuration des ports

- **Port** : `8080`
- C'est le port utilisé par nginx dans le Dockerfile du site

### Étape 3 : Déployer

1. **Cliquez sur "Deploy"**
2. **Attendre le build** (2-3 minutes)
3. **Vérifier les logs**

**Logs attendus :**
```
nginx: [notice] ready to handle requests
```

### Étape 4 : Vérifier l'accès

Une fois déployé, Dokploy vous donnera une URL publique.
- Exemple : `https://votre-app-site.dokploy.com`
- Le site devrait s'afficher

---

## 🔗 Configuration des domaines

### Pour l'application Bot

1. **Dans Dokploy, ouvrez l'application bot**
2. **Allez dans "Settings" ou "Paramètres"**
3. **Section "Domains" ou "Domaines"**
4. **Ajoutez le domaine** : `app.lesbricolesdelekmane.fun`
5. **Configurez les DNS** selon les instructions Dokploy

**Configuration DNS (exemple) :**
```
Type: CNAME
Name: app
Value: votre-instance-dokploy.com
TTL: 3600
```

### Pour l'application Site

1. **Dans Dokploy, ouvrez l'application site**
2. **Section "Domains"**
3. **Ajoutez le domaine** : `psg.lesbricolesdelekmane.fun`
4. **Configurez les DNS**

**Configuration DNS (exemple) :**
```
Type: CNAME
Name: psg
Value: votre-instance-dokploy.com
TTL: 3600
```

### Vérifier la configuration DNS

Attendez 5-10 minutes après la configuration DNS, puis testez :

```bash
# Test du bot
curl https://app.lesbricolesdelekmane.fun/api/status

# Test du site
curl https://psg.lesbricolesdelekmane.fun
```

---

## ✅ Vérification et tests

### Test 1 : API du bot

**URL à tester :** `https://app.lesbricolesdelekmane.fun/api/status`

**Méthode :**
1. Ouvrez votre navigateur
2. Allez sur : `https://app.lesbricolesdelekmane.fun/api/status`
3. Vous devriez voir un JSON avec les données du bot

**Réponse attendue :**
```json
{
  "bot_actif": true,
  "derniere_mise_a_jour": "21 décembre 2025 à 14:30:22",
  "matchs": [
    {
      "nom": "PSG vs PARIS FC",
      "url": "...",
      "pmr_disponible": false,
      "dernier_check": "Il y a 2 min",
      "nb_checks": 15
    }
  ],
  "statistiques": {
    "verifications_totales": 30,
    "alertes_envoyees": 0,
    "taux_disponibilite": "0%",
    "matchs_surveilles": 2
  }
}
```

### Test 2 : Site public

**URL à tester :** `https://psg.lesbricolesdelekmane.fun`

**Méthode :**
1. Ouvrez votre navigateur
2. Allez sur : `https://psg.lesbricolesdelekmane.fun`
3. Le site devrait s'afficher avec les données en temps réel
4. Les données se mettent à jour toutes les 10 secondes

**Vérifications :**
- ✅ Les cards de matchs s'affichent
- ✅ Les statistiques sont visibles
- ✅ Le footer affiche la dernière mise à jour
- ✅ Pas d'erreurs dans la console (F12)

### Test 3 : Interface admin

**URL à tester :** `https://psg.lesbricolesdelekmane.fun/admin.html`

**Méthode :**
1. Ouvrez votre navigateur
2. Allez sur : `https://psg.lesbricolesdelekmane.fun/admin.html`
3. Connectez-vous avec :
   - **Utilisateur** : `lek`
   - **Mot de passe** : `caca`

**Vérifications :**
- ✅ Le dashboard s'affiche
- ✅ Les statistiques du bot sont visibles
- ✅ Les matchs surveillés sont listés
- ✅ Les analytics du site sont affichées
- ✅ Pas d'erreurs dans la console

### Test 4 : Endpoints API

**Test avec curl ou Postman :**

```bash
# Test status
curl https://app.lesbricolesdelekmane.fun/api/status

# Test matches
curl https://app.lesbricolesdelekmane.fun/api/matches

# Test analytics
curl https://app.lesbricolesdelekmane.fun/api/analytics

# Test ajout match (POST)
curl -X POST https://app.lesbricolesdelekmane.fun/api/matches \
  -H "Content-Type: application/json" \
  -d '{"nom": "PSG vs TEST", "url": "https://example.com"}'
```

---

## 🎛️ Utilisation de l'interface admin

### Accéder à l'admin

1. **URL** : `https://psg.lesbricolesdelekmane.fun/admin.html`
2. **Identifiants** :
   - Utilisateur : `lek`
   - Mot de passe : `caca`

### Fonctionnalités disponibles

#### 1. Voir les statistiques

Le dashboard affiche :
- **Vérifications totales** : Nombre de checks effectués
- **Alertes envoyées** : Nombre d'alertes Telegram
- **Taux de disponibilité** : % de matchs avec PMR disponible
- **Matchs surveillés** : Nombre de matchs actifs

#### 2. Gérer les matchs

**Ajouter un match :**
1. Cliquez sur **"+ Ajouter"**
2. Remplissez :
   - **Nom du match** : Ex: `PSG vs LILLE`
   - **URL de la billetterie** : L'URL complète de la page de billetterie
3. Cliquez sur **"Ajouter"**
4. Le match est ajouté et le bot le détecte automatiquement

**Supprimer un match :**
1. Cliquez sur **"Supprimer"** à côté du match
2. Confirmez la suppression
3. Le match est retiré de la surveillance

**Forcer une vérification :**
1. Cliquez sur **"Vérifier"** à côté d'un match
2. Le bot vérifie immédiatement ce match (à implémenter)

#### 3. Voir les analytics

Le dashboard affiche :
- **Visiteurs totaux** : Nombre total de visiteurs
- **En ligne maintenant** : Visiteurs actuellement sur le site
- **Visiteurs aujourd'hui** : Visiteurs du jour
- **Temps moyen** : Temps moyen passé sur le site
- **Taux de rebond** : % de visiteurs qui partent immédiatement
- **Clics Telegram** : Nombre de clics sur le bouton Telegram
- **Pic de connexions** : Maximum de visiteurs simultanés
- **Taux de retour** : % de visiteurs qui reviennent

#### 4. Logs en temps réel

Les logs affichent :
- ✅ Actions réussies (vert)
- ❌ Erreurs (rouge)
- ℹ️ Informations (bleu)

Les logs se mettent à jour automatiquement toutes les 5 secondes.

---

## 🔧 Dépannage

### Problème 1 : Le bot ne démarre pas

**Symptômes :**
- Pas de logs dans Dokploy
- Application en erreur

**Solutions :**
1. **Vérifier les variables d'environnement**
   - Elles doivent être dans "Environment Settings", pas "Build-time Arguments"
   - Vérifiez les noms exacts : `TELEGRAM_TOKEN` et `TELEGRAM_CHAT_ID`

2. **Vérifier les logs de build**
   - Allez dans "Build Logs"
   - Cherchez les erreurs
   - Vérifiez que Playwright s'installe correctement

3. **Vérifier le Dockerfile**
   - Le Dockerfile doit être à la racine
   - Vérifiez que tous les fichiers sont copiés

### Problème 2 : L'API ne répond pas

**Symptômes :**
- `https://app.lesbricolesdelekmane.fun/api/status` retourne une erreur
- Erreur 404 ou 500

**Solutions :**
1. **Vérifier que le port 5000 est exposé**
   - Dans Dokploy, vérifiez la configuration des ports
   - Le port 5000 doit être accessible

2. **Vérifier les logs**
   - Cherchez le message : `🔌 API Flask démarrée sur le port 5000`
   - Si absent, l'API n'a pas démarré

3. **Vérifier les routes**
   - L'URL doit être : `/api/status` (avec `/api/` au début)
   - Pas juste `/status`

### Problème 3 : Le site ne charge pas les données

**Symptômes :**
- Le site s'affiche mais les données sont vides
- Erreurs dans la console du navigateur (F12)

**Solutions :**
1. **Vérifier l'URL du bot dans index.html**
   - Doit être : `https://app.lesbricolesdelekmane.fun`
   - Vérifiez dans le code source (F12 → Network)

2. **Vérifier CORS**
   - L'API doit avoir les headers CORS
   - Vérifiez dans les logs que Flask démarre avec CORS

3. **Vérifier que status.json existe**
   - Testez : `https://app.lesbricolesdelekmane.fun/status.json`
   - Doit retourner du JSON

### Problème 4 : Playwright ne fonctionne pas

**Symptômes :**
- Erreur : "Chromium not found"
- Erreur : "Browser launch failed"

**Solutions :**
1. **Vérifier l'installation de Playwright**
   - Dans les logs de build, cherchez : `playwright install chromium`
   - Doit s'installer sans erreur

2. **Vérifier les dépendances système**
   - Le Dockerfile installe toutes les dépendances nécessaires
   - Vérifiez que le build se termine sans erreur

3. **Vérifier les arguments Chrome**
   - Dans `psm.py`, vérifiez que `headless=True`
   - Vérifiez les arguments : `--no-sandbox`, etc.

### Problème 5 : Les matchs ne se chargent pas

**Symptômes :**
- L'admin affiche "Erreur de chargement"
- Les matchs ne s'affichent pas

**Solutions :**
1. **Vérifier que matches.json existe**
   - Le bot crée automatiquement ce fichier au démarrage
   - Vérifiez dans les logs

2. **Vérifier l'endpoint API**
   - Testez : `https://app.lesbricolesdelekmane.fun/api/matches`
   - Doit retourner un tableau de matchs

3. **Vérifier les permissions**
   - Le bot doit pouvoir créer/écrire `matches.json`
   - Vérifiez les permissions dans Docker

### Problème 6 : Les analytics ne fonctionnent pas

**Symptômes :**
- Les statistiques du site restent à 0
- Pas de tracking des visiteurs

**Solutions :**
1. **Vérifier l'endpoint de tracking**
   - Testez : `https://app.lesbricolesdelekmane.fun/api/analytics/visitor`
   - Doit retourner `{"success": true}`

2. **Vérifier que analytics.json est créé**
   - Le fichier est créé automatiquement au premier appel
   - Vérifiez dans les logs

3. **Vérifier les erreurs CORS**
   - Ouvrez la console du navigateur (F12)
   - Cherchez les erreurs CORS
   - L'API doit avoir les headers CORS configurés

---

## 📞 Support et ressources

### Fichiers importants

- **psm.py** : Bot principal + API Flask
- **requirements.txt** : Dépendances Python
- **Dockerfile** : Configuration Docker pour le bot
- **Site/index.html** : Site public
- **Site/admin.html** : Interface admin
- **Site/Dockerfile** : Configuration Docker pour le site

### URLs importantes

- **Bot + API** : `https://app.lesbricolesdelekmane.fun`
- **Site public** : `https://psg.lesbricolesdelekmane.fun`
- **Admin** : `https://psg.lesbricolesdelekmane.fun/admin.html`
- **API Status** : `https://app.lesbricolesdelekmane.fun/api/status`
- **API Matches** : `https://app.lesbricolesdelekmane.fun/api/matches`
- **API Analytics** : `https://app.lesbricolesdelekmane.fun/api/analytics`

### Commandes utiles

```bash
# Vérifier les logs du bot (dans Dokploy)
# Allez dans l'application bot → Logs

# Tester l'API
curl https://app.lesbricolesdelekmane.fun/api/status

# Vérifier les fichiers générés
# Dans Dokploy, allez dans l'application bot → Files
# Vous devriez voir : status.json, matches.json, analytics.json
```

---

## ✅ Checklist finale

Avant de considérer le déploiement comme terminé, vérifiez :

### Application Bot
- [ ] Application créée sur Dokploy
- [ ] Dépôt GitHub connecté
- [ ] Ports 8081 et 5000 configurés
- [ ] Variables d'environnement configurées (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
- [ ] Build réussi sans erreurs
- [ ] Logs runtime affichent : "API Flask démarrée" et "Serveur web démarré"
- [ ] Test API : `https://app.lesbricolesdelekmane.fun/api/status` fonctionne
- [ ] Domaine configuré (optionnel)

### Application Site
- [ ] Application créée sur Dokploy
- [ ] Root Directory configuré à `Site/`
- [ ] Port 8080 configuré
- [ ] Build réussi
- [ ] Site accessible
- [ ] Domaine configuré (optionnel)

### Tests fonctionnels
- [ ] Site public affiche les données
- [ ] Données se mettent à jour toutes les 10 secondes
- [ ] Interface admin accessible
- [ ] Connexion admin fonctionne
- [ ] Statistiques s'affichent dans l'admin
- [ ] Ajout de match fonctionne
- [ ] Suppression de match fonctionne
- [ ] Analytics se mettent à jour

### Bot
- [ ] Bot vérifie les matchs toutes les ~90 secondes
- [ ] Messages Telegram envoyés quand PMR disponible
- [ ] status.json généré et mis à jour
- [ ] matches.json créé et modifiable via l'API

---

---

## 🔥 Configuration Firebase (Optionnel mais Recommandé)

Firebase Firestore permet de persister toutes vos données (matchs, status, analytics, cache Groq, historique des détections) dans le cloud, évitant ainsi la perte de données lors des redéploiements.

### 📋 Prérequis

1. Un compte Google (gratuit)
2. Accès à la console Firebase : https://console.firebase.google.com/

### 🚀 Étapes de Configuration

#### 1. Créer un Projet Firebase

1. Allez sur https://console.firebase.google.com/
2. Cliquez sur **"Ajouter un projet"** (ou "Add project")
3. Entrez un nom pour votre projet (ex: `psm-bot` ou `psg-pmr-bot`)
4. Désactivez Google Analytics (optionnel, mais recommandé pour simplifier)
5. Cliquez sur **"Créer le projet"** puis **"Continuer"**

#### 2. Activer Firestore Database

1. Dans la console Firebase, ouvrez le menu de gauche
2. Allez dans **"Firestore Database"** (ou "Build" > "Firestore Database")
3. Cliquez sur **"Créer une base de données"**
4. Choisissez le mode :
   - **Mode production** (recommandé)
   - **Région** : `europe-west` (ou `europe-west1` pour la France)
5. Cliquez sur **"Activer"**

#### 3. Configurer les Règles de Sécurité Firestore

1. Dans Firestore Database, allez dans l'onglet **"Règles"**
2. Remplacez les règles par :

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Autoriser la lecture publique, écriture uniquement via Admin SDK
    match /matches/{matchId} {
      allow read: if true;
      allow write: if false;
    }
    
    match /status/{document} {
      allow read: if true;
      allow write: if false;
    }
    
    match /analytics/{document} {
      allow read: if true;
      allow write: if false;
    }
    
    match /groq_cache/{document} {
      allow read: if false;
      allow write: if false;
    }
    
    match /detections/{document} {
      allow read: if true;
      allow write: if false;
    }
  }
}
```

3. Cliquez sur **"Publier"**

> **Note** : L'écriture se fait uniquement via l'Admin SDK côté serveur (avec les credentials), donc ces règles sont principalement pour la sécurité.

#### 4. Créer une Clé de Compte de Service

1. Dans la console Firebase, cliquez sur l'icône ⚙️ (**Paramètres du projet**)
2. Allez dans l'onglet **"Comptes de service"**
3. Cliquez sur **"Générer une nouvelle clé privée"**
4. Une fenêtre s'ouvre : cliquez sur **"Générer la clé"**
5. Un fichier JSON est téléchargé (ex: `psm-bot-xxxxx-firebase-adminsdk-xxxxx.json`)
6. **⚠️ IMPORTANT** : Conservez ce fichier en sécurité et ne le commitez JAMAIS sur GitHub

#### 5. Obtenir le Project ID

1. Dans **Paramètres du projet** > **Général**
2. Notez le **Project ID** (ex: `psm-bot-7140d`)

#### 6. Configurer dans Dokploy

1. Ouvrez votre **application Bot** dans Dokploy
2. Allez dans **"Variables d'environnement"**
3. Ajoutez ces variables :

**Variable 1 : `FIREBASE_PROJECT_ID`**
```
Valeur : votre-project-id (ex: psm-bot-7140d)
```

**Variable 2 : `FIREBASE_CREDENTIALS`**
```
Valeur : Le contenu COMPLET du fichier JSON téléchargé (en une seule ligne, sans retours à la ligne)
```

> **Comment obtenir la valeur de `FIREBASE_CREDENTIALS` :**
> 1. Ouvrez le fichier JSON téléchargé à l'étape 4
> 2. Copiez TOUT le contenu (Ctrl+A, Ctrl+C)
> 3. Collez-le dans la variable d'environnement (Dokploy gère automatiquement les retours à la ligne)
> 
> **⚠️ Si vous avez des erreurs de parsing JSON**, utilisez la méthode alternative ci-dessous.

#### 6.1 Alternative : Utiliser un fichier (Recommandé si erreur de parsing)

Si vous rencontrez des erreurs de parsing JSON avec la variable `FIREBASE_CREDENTIALS`, vous pouvez utiliser un fichier à la place :

**Méthode 1 : Via le Dockerfile (Recommandé si repo privé)**

1. **Ajoutez le fichier JSON au dépôt** :
   - Renommez le fichier téléchargé en `firebase-credentials.json`
   - Placez-le à la racine du projet (même niveau que `psm.py`)
   - **⚠️ IMPORTANT** : Cette méthode est acceptable UNIQUEMENT si votre repo GitHub est **PRIVÉ** !
   - Si votre repo est public, utilisez plutôt la variable d'environnement `FIREBASE_CREDENTIALS`

2. **Le Dockerfile** copie automatiquement le fichier :
   ```dockerfile
   COPY firebase-credentials.json /app/firebase-credentials.json
   ```
   - Le fichier sera copié dans le container au build

3. **Commitez le fichier sur GitHub** :
   ```bash
   git add firebase-credentials.json Dockerfile
   git commit -m "Ajout firebase-credentials.json (repo privé)"
   git push
   ```
   - **⚠️ SÉCURITÉ** : Vérifiez que votre repo GitHub est bien **PRIVÉ** avant de commiter !

4. **Configurez la variable d'environnement dans Dokploy** :
   - **Nom** : `FIREBASE_CREDENTIALS_PATH`
   - **Valeur** : `/app/firebase-credentials.json`
   - **Supprimez** la variable `FIREBASE_CREDENTIALS` si elle existe

5. **Déployez** : Le fichier sera automatiquement copié dans le container au build

**Méthode 2 : Via un volume mount (Si Dokploy le supporte)**

1. **Dans Dokploy**, allez dans les paramètres de votre application Bot
2. Cherchez la section **"Volumes"** ou **"Volume Mounts"**
3. Configurez un volume :
   - **Host Path** : Chemin vers votre fichier `firebase-credentials.json` sur le serveur Dokploy
   - **Container Path** : `/app/firebase-credentials.json`
   - **Type** : `bind` ou `volume`

4. **Configurez la variable d'environnement** :
   - **Nom** : `FIREBASE_CREDENTIALS_PATH`
   - **Valeur** : `/app/firebase-credentials.json`
   - **Supprimez** la variable `FIREBASE_CREDENTIALS` si elle existe

**Méthode 3 : Via Secrets Dokploy (Si disponible)**

1. **Dans Dokploy**, allez dans **"Secrets"** ou **"Files"**
2. **Uploadez** le fichier `firebase-credentials.json`
3. Dokploy vous donnera un chemin (ex: `/secrets/firebase-credentials.json`)
4. **Configurez la variable d'environnement** :
   - **Nom** : `FIREBASE_CREDENTIALS_PATH`
   - **Valeur** : Le chemin fourni par Dokploy (ex: `/secrets/firebase-credentials.json`)

**⚠️ Sécurité** : Quelle que soit la méthode, assurez-vous que le fichier n'est **JAMAIS** commité sur GitHub !

#### 7. Redémarrer l'Application

1. Redémarrez l'application Bot dans Dokploy
2. Vérifiez les logs : vous devriez voir :
   ```
   ✅ Credentials Firebase chargés depuis FIREBASE_CREDENTIALS
   ✅ Firebase initialisé avec succès (Project ID: psm-bot-7140d)
   📥 Chargement des données depuis Firestore...
   ✅ X match(s) chargé(s) depuis Firestore
   ✅ Status chargé depuis Firestore
   ✅ Analytics chargé(s) depuis Firestore
   ✅ Cache Groq chargé depuis Firestore (X entrée(s))
   ✅ X détection(s) chargée(s) depuis Firestore
   ✅ Toutes les données ont été chargées depuis Firestore
   ```

#### 8. Vérifier dans la Console Firebase

1. Allez dans **Firestore Database** > **Données**
2. Vous devriez voir les collections créées automatiquement :
   - `matches/` : Liste des matchs surveillés
   - `status/` : État actuel du bot
   - `analytics/` : Statistiques du site
   - `groq_cache/` : Cache des analyses Groq
   - `detections/` : Historique des détections PMR

### 📊 Structure des Données dans Firestore

```
psm-bot/
  ├── matches/              (Collection)
  │   ├── PSG_vs_OM/        (Document)
  │   │   ├── nom: "PSG vs OM"
  │   │   ├── url: "https://..."
  │   │   ├── competition: "Ligue 1"
  │   │   ├── date: "2025-01-15"
  │   │   ├── time: "21:00"
  │   │   └── lieu: "Parc des Princes"
  │   └── PSG_vs_LILLE/     (Document)
  │
  ├── status/               (Collection)
  │   └── current/          (Document unique)
  │       ├── bot_actif: true
  │       ├── matchs: [...]
  │       └── statistiques: {...}
  │
  ├── analytics/            (Collection)
  │   └── current/          (Document unique)
  │       ├── visiteurs_totaux: 500
  │       ├── visiteurs_en_ligne: 10
  │       └── historique_7j: [...]
  │
  ├── groq_cache/           (Collection)
  │   ├── PSG vs OM/        (Document par match)
  │   │   ├── analysis: {...}
  │   │   ├── last_updated: "2025-01-10T10:00:00"
  │   │   └── match_name: "PSG vs OM"
  │   └── PSG vs LILLE/     (Document)
  │
  └── detections/           (Collection)
      ├── 2025-01-10T10:00:00_PSG_vs_OM/  (Document)
      │   ├── match: "PSG vs OM"
      │   ├── nb_places: 3
      │   ├── date: "2025-01-10T10:00:00"
      │   └── date_formatee: "10 janvier 2025 à 10:00:00"
      └── ...
```

### 🔄 Migration des Données Existantes

Si vous avez déjà des données dans `matches.json`, `status.json`, etc. :

1. **Au premier démarrage avec Firebase** : Le bot chargera d'abord depuis Firestore
2. **Si Firestore est vide** : Il utilisera les fichiers JSON locaux
3. **Les nouvelles données** seront automatiquement sauvegardées dans Firestore ET dans les fichiers JSON locaux (double sécurité)

### 💰 Coûts Firebase

Firestore a un **plan gratuit généreux** :
- **50 000 lectures/jour** (gratuit)
- **20 000 écritures/jour** (gratuit)
- **20 000 suppressions/jour** (gratuit)
- **1 Go de stockage** (gratuit)

Pour un bot de surveillance, ces limites sont largement suffisantes.

### ⚠️ Points Importants

- **Sécurité** : Le fichier JSON de credentials ne doit **JAMAIS** être commité sur GitHub
- **Backup** : Le bot sauvegarde aussi dans les fichiers JSON locaux en parallèle (double sécurité)
- **Performance** : Firestore est très rapide et accessible depuis n'importe où
- **Compatibilité** : Le système fonctionne avec ou sans Firebase (fallback automatique)

### 🐛 Dépannage

**Problème** : `FIREBASE_PROJECT_ID non défini`
- **Solution** : Vérifiez que la variable d'environnement est bien définie dans Dokploy

**Problème** : `Erreur parsing FIREBASE_CREDENTIALS`
- **Solution** : Vérifiez que le JSON est valide et copié en entier (sans retours à la ligne supplémentaires)

**Problème** : `Erreur initialisation Firebase`
- **Solution** : Vérifiez les logs pour voir l'erreur exacte. Vérifiez que le Project ID correspond bien au `project_id` dans le JSON des credentials.

**Problème** : Les données ne se chargent pas depuis Firestore
- **Solution** : Vérifiez que Firestore est bien activé dans la console Firebase et que les règles de sécurité permettent la lecture.

---

## 🎉 Félicitations !

Si tous les éléments de la checklist sont cochés, votre bot est opérationnel !

**Prochaines étapes :**
- Surveiller les logs régulièrement
- Ajouter/supprimer des matchs via l'interface admin
- Consulter les analytics pour suivre l'utilisation
- Personnaliser les messages Telegram si besoin
- **Configurer Firebase pour persister vos données** (recommandé)

**Bonne chance avec votre bot PSG PMR ! 🚀**



