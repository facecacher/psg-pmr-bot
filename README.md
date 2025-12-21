# PSG PMR Bot - Surveille les places PMR pour toi

Salut ! Ce bot a été créé pour résoudre un problème simple mais chiant : trouver des places PMR pour les matchs du PSG, c'est un vrai parcours du combattant. Les places se libèrent de manière aléatoire, et si tu rates le coche, c'est mort. Du coup, j'ai fait ce bot qui surveille la billetterie en continu et qui t'envoie une alerte Telegram dès qu'une place PMR se libère.

## Le problème de base

Alors voilà le truc : quand tu veux aller voir un match du PSG et que tu as besoin d'une place PMR, c'est la galère. La billetterie du PSG met les places PMR en vente de manière assez aléatoire, et elles partent super vite. Si tu ne checkes pas toutes les 5 minutes, tu rates tout. Et franchement, personne n'a envie de rafraîchir une page toutes les 5 minutes pendant des jours.

L'idée c'était simple : créer un bot qui fait ce boulot chiant à ma place. Il surveille la billetterie en continu, et dès qu'une place PMR apparaît, il m'envoie un message Telegram. Comme ça, je peux être notifié instantanément et réserver avant que ce soit trop tard.

## Comment ça marche (l'idée)

Le principe est assez simple dans le fond. Le bot utilise Playwright (un outil qui peut contrôler un navigateur comme un vrai humain) pour ouvrir la page de billetterie du PSG. Il charge la page complètement, fait défiler pour s'assurer que tout le contenu dynamique est chargé, puis il cherche tous les éléments HTML qui correspondent aux places PMR.

Quand il trouve des places PMR disponibles, il envoie un message sur Telegram pour m'alerter. Si pas de place, il attend un peu (environ 90 secondes) et recommence. Comme ça, il surveille en continu sans que j'aie à m'en occuper.

Au début, c'était juste un script Python qui tournait sur mon PC. Mais bon, laisser mon ordi allumé 24/7 juste pour ça, c'était pas top. Du coup, j'ai containerisé le truc avec Docker et je l'ai déployé sur Dokploy pour qu'il tourne en permanence sur un serveur.

## L'évolution du projet

Au début, c'était vraiment basique : un script qui checkait une page et envoyait un message Telegram. Mais au fur et à mesure, j'ai ajouté des trucs qui me semblaient utiles.

D'abord, j'ai voulu voir l'état du bot en temps réel. Du coup, j'ai créé un fichier `status.json` qui contient toutes les infos : quels matchs sont surveillés, combien de fois chaque match a été vérifié, si des places PMR sont disponibles, etc. Et j'ai fait un petit site web qui lit ce fichier et affiche tout ça de manière sympa.

Ensuite, j'ai voulu pouvoir gérer les matchs facilement. Au lieu de modifier le code à chaque fois, j'ai créé un système où les matchs sont stockés dans un fichier `matches.json`. Comme ça, je peux ajouter ou supprimer des matchs sans toucher au code.

Puis j'ai créé une interface admin pour gérer tout ça depuis le web. Tu peux ajouter des matchs, en supprimer, forcer une vérification, voir les stats... Et surtout, tu vois les vrais logs du bot en temps réel, comme si tu regardais la console du serveur. C'est beaucoup plus pratique que de se connecter en SSH pour voir ce qui se passe.

J'ai aussi ajouté un système d'analytics basique pour le site web : nombre de visiteurs, clics sur le bouton Telegram, etc. Rien de fou, mais ça donne une idée de l'utilisation.

## L'architecture technique

Bon, maintenant on rentre dans le technique. Le projet est structuré en plusieurs parties qui tournent ensemble.

### Le bot principal (psm.py)

C'est le cœur du système. C'est un script Python qui fait plusieurs choses en parallèle grâce au threading.

**La boucle de surveillance** : Le bot charge la liste des matchs depuis `matches.json`, puis pour chaque match, il lance Playwright. Playwright ouvre un navigateur Chromium en mode headless (sans interface graphique, parfait pour un serveur), charge la page de billetterie, fait défiler pour charger tout le contenu dynamique, puis cherche les éléments HTML avec l'attribut `data-offer-type="PMR"`. Si il en trouve, c'est qu'il y a des places disponibles, et il envoie un message Telegram. Sinon, il attend un peu et recommence.

**Le serveur web intégré** : En parallèle, le bot lance un serveur HTTP simple qui sert deux choses. D'abord, il sert le fichier `status.json` qui contient l'état actuel du bot. Ensuite, il sert les fichiers statiques du site web (index.html, admin.html) depuis le dossier `Site/`. Ce serveur tourne sur le port 8081.

**L'API Flask** : J'ai aussi intégré une API Flask qui tourne sur le port 5000. Cette API permet de gérer les matchs (ajouter, supprimer, lister), de récupérer les stats, et surtout de récupérer les logs du backend en temps réel. L'API est accessible via des endpoints REST classiques : `/api/matches` pour les matchs, `/api/status` pour le statut, `/api/logs` pour les logs, etc.

**Le système de logs** : Tous les `print()` importants sont interceptés et stockés dans une liste en mémoire (limitée à 200 logs pour pas saturer la RAM). Chaque log a un timestamp et un type (success, error, warning, info). L'interface admin peut récupérer ces logs via l'API et les afficher avec une jolie présentation.

### Le site public (Site/index.html)

C'est l'interface que tout le monde peut voir. Le site charge `status.json` toutes les 10 secondes et affiche les infos de manière dynamique. Les cards de matchs sont créées automatiquement selon ce qui est dans `status.json`, donc si tu ajoutes un match, il apparaît automatiquement sur le site.

Le site affiche pour chaque match : le nom, si des places PMR sont disponibles, quand a eu lieu le dernier check, et combien de vérifications ont été faites. Il y a aussi des stats globales : nombre total de vérifications, nombre d'alertes envoyées, taux de disponibilité, etc.

### L'interface admin (Site/admin.html)

C'est l'interface privée pour gérer le bot. Il faut se connecter avec un login/mot de passe (c'est basique mais ça fait le job). Une fois connecté, tu peux :

- Voir les stats du bot et du site en temps réel
- Ajouter des matchs à surveiller (juste le nom et l'URL de la page de billetterie)
- Supprimer des matchs
- Forcer une vérification immédiate d'un match
- Voir les vrais logs du backend en temps réel (mis à jour toutes les 3 secondes)

Les logs affichent exactement ce qui se passe dans le backend : quand un match est ajouté, quand une vérification est lancée, quand une page est chargée, combien de places PMR sont trouvées, etc. C'est super pratique pour débugger ou juste voir ce qui se passe.

### Le système de fichiers JSON

Le bot utilise trois fichiers JSON pour stocker les données :

- **matches.json** : La liste des matchs à surveiller. C'est un simple tableau JSON avec des objets qui contiennent `nom` et `url`. Ce fichier peut être modifié via l'API ou directement sur le serveur.

- **status.json** : L'état actuel du bot. Il est régénéré à chaque vérification et contient les infos de chaque match (disponibilité PMR, dernier check, nombre de vérifications) ainsi que des stats globales. C'est ce fichier que le site public lit pour afficher les données.

- **analytics.json** : Les stats du site web (visiteurs, clics Telegram, etc.). C'est mis à jour à chaque visite et à chaque clic sur le bouton Telegram.

### Le déploiement

Le bot est containerisé avec Docker. Le Dockerfile installe toutes les dépendances système nécessaires pour Playwright (Chromium et toutes ses dépendances), installe les packages Python, et lance le script principal.

Pour le déploiement, j'utilise Dokploy qui est super pratique. J'ai deux applications séparées :

1. **L'application bot** : C'est le bot principal avec l'API Flask. Elle tourne sur les ports 8081 (serveur web) et 5000 (API Flask). C'est cette app qui fait tout le boulot de surveillance.

2. **L'application site** : C'est juste le site web statique (index.html et admin.html). Elle tourne sur le port 8080 avec un serveur HTTP simple. C'est séparé pour pouvoir avoir des domaines différents si besoin.

Les deux apps sont déployées depuis le même repo GitHub, mais l'app site utilise le dossier `Site/` comme root directory.

## Les détails techniques qui comptent

### Playwright et le headless

Playwright est l'outil qui permet de contrôler un navigateur programmatiquement. C'est comme Selenium mais en mieux. Le bot lance Chromium en mode headless (sans interface graphique) avec des arguments spécifiques pour Docker : `--no-sandbox`, `--disable-setuid-sandbox`, etc. Ces arguments sont nécessaires pour que ça fonctionne dans un container Docker.

Le chargement des pages est fait de manière progressive : d'abord on charge la page avec `domcontentloaded`, on attend 10 secondes pour que le JavaScript charge tout, puis on fait défiler plusieurs fois pour déclencher le chargement du contenu dynamique (souvent les sites chargent du contenu au scroll). Ensuite on cherche les éléments PMR.

### La gestion des matchs

Les matchs sont stockés dans `matches.json` et chargés à chaque cycle de la boucle principale. Comme ça, si tu ajoutes un match via l'API, il sera pris en compte au prochain cycle (environ 90 secondes). Si tu veux une vérification immédiate, tu peux utiliser le bouton "Vérifier" dans l'admin qui lance une vérification en arrière-plan.

Quand tu ajoutes ou supprimés un match, le bot met à jour `status.json` immédiatement. Comme ça, le site public reflète les changements rapidement (au prochain refresh, soit 10 secondes max).

### Le système de logs

Tous les logs importants passent par la fonction `log()` qui fait deux choses : elle affiche dans la console (pour les logs Dokploy) et elle stocke dans `backend_logs` (une deque limitée à 200 éléments). L'interface admin récupère ces logs via `/api/logs` et les affiche avec des couleurs selon le type.

### Le proxy API

Le serveur web (port 8081) fait un proxy vers l'API Flask (port 5000) pour les requêtes `/api/*`. Comme ça, tout passe par le même domaine et on évite les problèmes CORS. Le proxy exclut les headers CORS de Flask pour éviter les doublons (le serveur web gère CORS lui-même).

### Les analytics

Le tracking est super simple : à chaque visite du site, le JavaScript fait un POST vers `/api/analytics/visitor`. Le backend incrémente les compteurs dans `analytics.json`. Pour les clics Telegram, c'est pareil mais avec `/api/analytics/telegram-click`. L'historique des 7 derniers jours est géré automatiquement : à chaque nouveau jour, l'historique est décalé et le compteur du jour actuel est mis à jour.

## Utilisation

### Ajouter un match

Pour ajouter un match à surveiller, tu as deux options :

1. Via l'interface admin : Connecte-toi, clique sur "+ Ajouter", remplis le nom et l'URL de la page de billetterie, et valide. Le match sera ajouté et vérifié au prochain cycle.

2. Via l'API : Fais un POST vers `/api/matches` avec un JSON contenant `nom` et `url`.

3. Directement dans `matches.json` : Tu peux éditer le fichier sur le serveur, mais c'est moins pratique.

### Voir ce qui se passe

L'interface admin affiche les vrais logs du backend en temps réel. Tu vois exactement ce qui se passe : quand un match est vérifié, combien de places PMR sont trouvées, les erreurs éventuelles, etc. Les logs se mettent à jour toutes les 3 secondes automatiquement.

### Les notifications Telegram

Le bot envoie deux types de messages :

- **Quand des places PMR sont disponibles** : Un message d'alerte immédiat pour que tu puisses réserver vite.

- **Quand pas de place** : Un message toutes les 8 heures pour te tenir informé que le bot surveille toujours (avec un cooldown pour éviter le spam).

## Déploiement

Le projet est prêt pour être déployé sur Dokploy. Il y a un guide détaillé dans `GUIDE_DEPLOIEMENT.md` qui explique tout étape par étape.

En gros, il faut :
1. Créer deux applications sur Dokploy (une pour le bot, une pour le site)
2. Configurer les variables d'environnement (TELEGRAM_TOKEN et TELEGRAM_CHAT_ID)
3. Configurer les ports (8081 et 5000 pour le bot, 8080 pour le site)
4. Déployer

Le bot fonctionne en mode headless avec tous les arguments nécessaires pour Docker, donc ça devrait tourner sans problème.

## Structure du projet

```
psm-bot/
├── psm.py                 # Le bot principal (surveillance + API + serveur web)
├── requirements.txt        # Dépendances Python
├── Dockerfile             # Image Docker pour le bot
├── README.md              # Ce fichier
├── GUIDE_DEPLOIEMENT.md   # Guide de déploiement détaillé
└── Site/
    ├── index.html         # Site public
    ├── admin.html         # Interface admin
    └── Dockerfile         # Image Docker pour le site
```

Les fichiers `matches.json`, `status.json` et `analytics.json` sont générés automatiquement et ne sont pas versionnés.

## Dépendances

- **Playwright** : Pour contrôler le navigateur et scraper les pages
- **Flask** : Pour l'API REST
- **Flask-CORS** : Pour gérer les requêtes cross-origin
- **Requests** : Pour les appels à l'API Telegram

Tout est dans `requirements.txt`.

## Notes

Le bot est conçu pour tourner 24/7 sur un serveur. Il consomme pas mal de ressources (Playwright + Chromium), donc prévois au moins 1-2 Go de RAM. Sur Dokploy, ça tourne bien avec les ressources par défaut.

Les logs sont stockés en mémoire (max 200), donc ils seront perdus au redémarrage. Si tu veux garder les logs, il faudrait les sauvegarder dans un fichier, mais pour l'instant c'est pas nécessaire.

Le système est assez robuste : si une vérification échoue, le bot continue avec les autres matchs. Les erreurs sont loggées et tu peux les voir dans l'interface admin.

Voilà, c'est à peu près tout. Si tu as des questions ou des suggestions, n'hésite pas !
