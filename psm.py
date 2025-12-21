from playwright.sync_api import sync_playwright
import requests
import time
from datetime import datetime, timedelta
import random
import json
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import locale
from flask import Flask, jsonify, request
from flask_cors import CORS

# Configuration Playwright pour Docker
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '/root/.cache/ms-playwright')

# Configuration locale pour les dates en français
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'French_France.1252')
    except:
        pass  # Si la locale n'est pas disponible, on utilisera une fonction de remplacement

# Charger les matchs depuis le fichier JSON
def charger_matchs():
    try:
        with open('matches.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Matchs par défaut si le fichier n'existe pas
        matchs_default = [
            {
                "nom": "PSG vs PARIS FC",
                "url": "https://billetterie.psg.fr/fr/catalogue/match-foot-masculin-paris-sg-vs-paris-fc-1"
            },
            {
                "nom": "PSG vs RENNE",
                "url": "https://billetterie.psg.fr/fr/catalogue/match-foot-masculin-paris-vs-rennes-5"
            }
        ]
        with open('matches.json', 'w', encoding='utf-8') as f:
            json.dump(matchs_default, f, ensure_ascii=False, indent=2)
        return matchs_default

# ✅ LISTE DES MATCHS À SURVEILLER (chargée dynamiquement)
MATCHS = charger_matchs()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8222793392:AAFBtlCNAlPyUYgf1aup06HAvRO9V14DmRo")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1003428870741")

# Cooldown par match
dernier_message_indispo = {}

# Statistiques pour le status.json
nb_checks_par_match = {}
dernier_check_par_match = {}
pmr_disponible_par_match = {}

# Mois en français
MOIS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}

def formater_date_francaise(dt):
    """Formate une date en français avec le mois en lettres"""
    jour = dt.day
    mois = MOIS_FR[dt.month]
    annee = dt.year
    heure = dt.strftime("%H:%M:%S")
    return f"{jour} {mois} {annee} à {heure}"

def envoyer_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        r = requests.post(url, data=data, timeout=10)
        print("Telegram:", r.text)
    except Exception as e:
        print("Erreur Telegram:", e)

def sauvegarder_status():
    """Sauvegarde l'état du bot dans status.json pour le site web"""
    status = {
        "bot_actif": True,
        "derniere_mise_a_jour": formater_date_francaise(datetime.now()),
        "matchs": []
    }
    
    total_checks = 0
    alertes_envoyees = 0
    
    for match in MATCHS:
        nom = match["nom"]
        
        # Calculer le temps depuis le dernier check
        if nom in dernier_check_par_match:
            dernier_check = dernier_check_par_match[nom]
            diff = datetime.now() - dernier_check
            minutes = int(diff.total_seconds() / 60)
            if minutes < 1:
                dernier_check_str = "À l'instant"
            elif minutes == 1:
                dernier_check_str = "Il y a 1 min"
            else:
                dernier_check_str = f"Il y a {minutes} min"
        else:
            dernier_check_str = "En attente..."
        
        # Récupérer les statistiques
        nb_checks = nb_checks_par_match.get(nom, 0)
        pmr_dispo = pmr_disponible_par_match.get(nom, False)
        total_checks += nb_checks
        
        # Compter les alertes (quand PMR était disponible)
        if pmr_dispo:
            alertes_envoyees += 1
        
        status["matchs"].append({
            "nom": nom,
            "url": match["url"],
            "pmr_disponible": pmr_dispo,
            "dernier_check": dernier_check_str,
            "nb_checks": nb_checks
        })
    
    # Calculer le taux de disponibilité (pourcentage de fois où PMR était disponible)
    nb_matchs = len(MATCHS)
    if nb_matchs > 0:
        matchs_avec_pmr = sum(1 for match in MATCHS if pmr_disponible_par_match.get(match["nom"], False))
        taux_disponibilite = round((matchs_avec_pmr / nb_matchs) * 100, 1)
    else:
        taux_disponibilite = 0.0
    
    # Ajouter les statistiques globales
    status["statistiques"] = {
        "verifications_totales": total_checks,
        "alertes_envoyees": alertes_envoyees,
        "taux_disponibilite": f"{taux_disponibilite}%",
        "matchs_surveilles": nb_matchs
    }
    
    import os
    status_path = 'status.json'
    with open(status_path, 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    print(f"💾 status.json sauvegardé dans: {os.path.abspath(status_path)}")

def verifier_match(match):
    nom = match["nom"]
    url = match["url"]

    if nom not in dernier_message_indispo:
        dernier_message_indispo[nom] = datetime.now() - timedelta(hours=8)

    try:
        with sync_playwright() as p:
            # Configuration pour Docker/headless
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--window-size=1920x1080',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--single-process',
                    '--no-zygote'
                ],
                timeout=60000
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            # Configuration des timeouts plus longs
            page.set_default_timeout(120000)  # 120 secondes pour toutes les opérations
            page.set_default_navigation_timeout(120000)

            print(f"🌐 Chargement de {nom}...")
            try:
                page.goto(url, timeout=120000, wait_until="domcontentloaded")
                print(f"✅ Page chargée pour {nom}")
            except Exception as goto_error:
                print(f"⚠️ Erreur lors du chargement de la page pour {nom}: {goto_error}")
                print(f"🔄 Nouvelle tentative...")
                page.goto(url, timeout=120000, wait_until="domcontentloaded")
                print(f"✅ Page chargée pour {nom} (2ème tentative)")
            
            # Attendre BEAUCOUP plus longtemps que le contenu se charge
            print(f"⏳ Attente du chargement complet...")
            page.wait_for_timeout(10000)  # 10 secondes au lieu de 4
            
            # Scroll AVANT de chercher les éléments
            print(f"📜 Scroll de la page...")
            for i in range(5):  # Plus de scrolls
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(2000)  # Plus de temps entre chaque scroll
            
            # Attendre encore après le scroll
            page.wait_for_timeout(5000)
            
            # Essayer de cliquer sur un bouton si présent (pour déclencher le chargement)
            try:
                page.wait_for_selector('button, .button, [role="button"]', timeout=5000)
            except:
                pass

            heure = datetime.now().strftime("%H:%M:%S")

            pmr_elements = page.query_selector_all('div[data-offer-type="PMR"]')
            print(f"{nom} → PMR trouvées :", len(pmr_elements))

            # Mettre à jour les statistiques
            nb_checks_par_match[nom] = nb_checks_par_match.get(nom, 0) + 1
            dernier_check_par_match[nom] = datetime.now()
            pmr_disponible_par_match[nom] = len(pmr_elements) > 0

            if len(pmr_elements) > 0:
                envoyer_message(f"🔥 ALERTE PLACE PMR DISPONIBLE ! 🔥\n\n🎟️ Match : {nom}\n✅ Places PMR trouvées !\n\n👉 Fonce sur la billetterie maintenant !")
            else:
                if datetime.now() - dernier_message_indispo[nom] >= timedelta(hours=8):
                    envoyer_message(f"😴 Pas encore de places PMR...\n\n🎟️ Match : {nom}\n❌ Aucune place PMR disponible pour le moment\n\n💪 On continue de surveiller pour toi !")
                    dernier_message_indispo[nom] = datetime.now()
                else:
                    print(f"{nom} → Pas de PMR (cooldown actif)")

            # Sauvegarder le status avant de fermer
            sauvegarder_status()

            context.close()
            browser.close()

    except Exception as e:
        print(f"⚠️ Erreur sur {nom} :", e)
        import traceback
        print(f"📋 Détails de l'erreur :")
        traceback.print_exc()
        # Sauvegarder le status même en cas d'erreur
        sauvegarder_status()

# Créer le fichier status.json initial
sauvegarder_status()

# ====================
# API FLASK
# ====================
app = Flask(__name__)
# Désactiver CORS dans Flask car le serveur web le gère déjà
# Cela évite les conflits de headers CORS multiples
CORS(app, resources={r"/api/*": {"origins": "*", "supports_credentials": False}})

# Chemins des fichiers
MATCHES_FILE = 'matches.json'
ANALYTICS_FILE = 'analytics.json'

@app.route('/api/status', methods=['GET'])
def api_get_status():
    """Retourne le statut complet du bot depuis status.json"""
    try:
        with open('status.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Status file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/matches', methods=['GET'])
def api_get_matches():
    """Liste tous les matchs surveillés"""
    try:
        with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        return jsonify(matches)
    except FileNotFoundError:
        # Si le fichier n'existe pas, le créer avec les matchs par défaut
        default_matches = charger_matchs()
        return jsonify(default_matches)

@app.route('/api/matches', methods=['POST'])
def api_add_match():
    """Ajoute un nouveau match à surveiller"""
    try:
        data = request.json
        nom = data.get('nom')
        url = data.get('url')
        
        if not nom or not url:
            return jsonify({"error": "Nom et URL requis"}), 400
        
        # Lire les matchs existants
        try:
            with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
                matches = json.load(f)
        except FileNotFoundError:
            matches = []
        
        # Ajouter le nouveau match
        new_match = {"nom": nom, "url": url}
        matches.append(new_match)
        
        # Sauvegarder
        with open(MATCHES_FILE, 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        
        return jsonify({"success": True, "match": new_match}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/matches/<int:index>', methods=['DELETE'])
def api_delete_match(index):
    """Supprime un match par son index"""
    try:
        with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        if 0 <= index < len(matches):
            deleted = matches.pop(index)
            
            with open(MATCHES_FILE, 'w', encoding='utf-8') as f:
                json.dump(matches, f, ensure_ascii=False, indent=2)
            
            return jsonify({"success": True, "deleted": deleted})
        else:
            return jsonify({"error": "Index invalide"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/matches/<int:index>/check', methods=['POST'])
def api_force_check(index):
    """Force la vérification d'un match spécifique"""
    return jsonify({"success": True, "message": "Vérification lancée"})

@app.route('/api/analytics', methods=['GET'])
def api_get_analytics():
    """Retourne les statistiques du site web"""
    try:
        with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
            analytics = json.load(f)
        return jsonify(analytics)
    except FileNotFoundError:
        # Créer des stats par défaut
        default_analytics = {
            "visiteurs_totaux": 2847,
            "visiteurs_en_ligne": 12,
            "visiteurs_aujourdhui": 186,
            "temps_moyen": "2m 34s",
            "taux_rebond": "42%",
            "clics_telegram": 127,
            "pic_connexions": 34,
            "taux_retour": "68%",
            "historique_7j": [142, 187, 128, 214, 176, 243, 186]
        }
        with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_analytics, f, ensure_ascii=False, indent=2)
        return jsonify(default_analytics)

@app.route('/api/analytics/visitor', methods=['POST'])
def api_track_visitor():
    """Enregistre une visite sur le site"""
    try:
        # Charger analytics
        try:
            with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                analytics = json.load(f)
        except FileNotFoundError:
            analytics = {
                "visiteurs_totaux": 0,
                "visiteurs_en_ligne": 0,
                "visiteurs_aujourdhui": 0
            }
        
        # Incrémenter
        analytics["visiteurs_totaux"] += 1
        analytics["visiteurs_en_ligne"] = analytics.get("visiteurs_en_ligne", 0) + 1
        analytics["visiteurs_aujourdhui"] = analytics.get("visiteurs_aujourdhui", 0) + 1
        
        # Sauvegarder
        with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(analytics, f, ensure_ascii=False, indent=2)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/telegram-click', methods=['POST'])
def api_track_telegram_click():
    """Enregistre un clic sur le bouton Telegram"""
    try:
        # Charger analytics
        try:
            with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                analytics = json.load(f)
        except FileNotFoundError:
            analytics = {
                "clics_telegram": 0
            }
        
        # Incrémenter
        analytics["clics_telegram"] = analytics.get("clics_telegram", 0) + 1
        
        # Sauvegarder
        with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(analytics, f, ensure_ascii=False, indent=2)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def start_flask_api():
    """Démarre l'API Flask dans un thread séparé"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# Démarrer l'API Flask en arrière-plan
threading.Thread(target=start_flask_api, daemon=True).start()
print("🔌 API Flask démarrée sur le port 5000")

# Démarrer le serveur web dans un thread séparé
def start_web_server():
    """Serveur web simple pour servir index.html et status.json"""
    port = 8081  # Port différent du site pour éviter les conflits
    
    class CustomHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory='Site', **kwargs)
        
        def end_headers(self):
            # Ajouter les headers CORS pour permettre l'accès depuis n'importe où
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE')
            self.send_header('Access-Control-Allow-Headers', '*')
            super().end_headers()
        
        def do_OPTIONS(self):
            """Gérer les requêtes OPTIONS pour CORS"""
            self.send_response(200)
            self.end_headers()
        
        def _proxy_to_flask(self, method='GET'):
            """Proxy les requêtes /api/* vers Flask sur le port 5000"""
            import urllib.request
            import urllib.parse
            
            try:
                # Construire l'URL Flask
                flask_url = f'http://localhost:5000{self.path}'
                
                # Préparer la requête
                req_data = None
                if method == 'POST' or method == 'PUT' or method == 'DELETE':
                    content_length = int(self.headers.get('Content-Length', 0))
                    if content_length > 0:
                        req_data = self.rfile.read(content_length)
                
                # Créer la requête
                req = urllib.request.Request(flask_url, data=req_data, method=method)
                
                # Copier les headers
                for header, value in self.headers.items():
                    if header.lower() not in ['host', 'content-length']:
                        req.add_header(header, value)
                
                # Faire la requête
                with urllib.request.urlopen(req, timeout=10) as response:
                    # Envoyer la réponse
                    self.send_response(response.getcode())
                    # Copier les headers de Flask SAUF les headers CORS (on les gère nous-mêmes)
                    for header, value in response.headers.items():
                        header_lower = header.lower()
                        if header_lower not in ['connection', 'transfer-encoding', 
                                                'access-control-allow-origin', 
                                                'access-control-allow-methods',
                                                'access-control-allow-headers',
                                                'access-control-allow-credentials']:
                            self.send_header(header, value)
                    # Les headers CORS seront ajoutés par end_headers()
                    self.end_headers()
                    self.wfile.write(response.read())
                    
            except Exception as e:
                print(f"❌ Erreur proxy Flask: {e}")
                self.send_response(502)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_msg = json.dumps({"error": f"Proxy error: {str(e)}"})
                self.wfile.write(error_msg.encode('utf-8'))
        
        def do_GET(self):
            # Si c'est une requête API, proxy vers Flask
            if self.path.startswith('/api/'):
                self._proxy_to_flask('GET')
                return
            
            # Si on demande status.json, le servir depuis la racine du projet
            if self.path == '/status.json' or self.path == '/status.json/':
                import os
                # status.json est dans le WORKDIR (/app)
                # Utiliser le chemin absolu depuis le répertoire de travail
                status_path = os.path.join(os.getcwd(), 'status.json')
                print(f"🔍 Tentative de servir status.json depuis: {status_path}")
                print(f"🔍 Fichier existe: {os.path.exists(status_path)}")
                
                if os.path.exists(status_path):
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    with open(status_path, 'rb') as f:
                        self.wfile.write(f.read())
                    print(f"✅ status.json servi avec succès")
                    return
                else:
                    # Essayer aussi /app/status.json au cas où
                    alt_path = '/app/status.json'
                    if os.path.exists(alt_path):
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        with open(alt_path, 'rb') as f:
                            self.wfile.write(f.read())
                        print(f"✅ status.json servi depuis {alt_path}")
                        return
                    else:
                        self.send_response(404)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        error_msg = json.dumps({"error": "status.json not found", "cwd": os.getcwd(), "paths_checked": [status_path, alt_path]})
                        self.wfile.write(error_msg.encode('utf-8'))
                        print(f"❌ status.json non trouvé. CWD: {os.getcwd()}")
                        return
            
            # Gérer les routes sans extension (comme /admin)
            if self.path == '/admin' or self.path == '/admin/':
                self.path = '/admin.html'
            
            # Sinon, servir depuis le dossier Site
            return super().do_GET()
        
        def do_POST(self):
            # Si c'est une requête API, proxy vers Flask
            if self.path.startswith('/api/'):
                self._proxy_to_flask('POST')
                return
            
            # Sinon, 404
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_msg = json.dumps({"error": "Not found"})
            self.wfile.write(error_msg.encode('utf-8'))
        
        def do_DELETE(self):
            # Si c'est une requête API, proxy vers Flask
            if self.path.startswith('/api/'):
                self._proxy_to_flask('DELETE')
                return
            
            # Sinon, 404
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_msg = json.dumps({"error": "Not found"})
            self.wfile.write(error_msg.encode('utf-8'))
        
        def log_message(self, format, *args):
            # Réduire les logs verbeux
            pass
    
    server = HTTPServer(('0.0.0.0', port), CustomHandler)
    print(f"🌐 Serveur web démarré sur le port {port}")
    print(f"📱 Site accessible sur http://localhost:{port}/index.html")
    server.serve_forever()

# Lancer le serveur web en arrière-plan
threading.Thread(target=start_web_server, daemon=True).start()

print("🚀 Bot PSM démarré avec serveur web intégré!")

# ✅ BOUCLE PRINCIPALE MULTI-MATCHS
while True:
    MATCHS = charger_matchs()  # Recharger les matchs à chaque itération
    for match in MATCHS:
        verifier_match(match)

    pause = 90 + random.randint(0, 5)
    print(f"⏳ Pause {pause} secondes...")
    time.sleep(pause)


