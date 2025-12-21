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

# ✅ LISTE DES MATCHS À SURVEILLER
MATCHS = [
    {
        "nom": "PSG vs PARIS FC",
        "url": "https://billetterie.psg.fr/fr/catalogue/match-foot-masculin-paris-sg-vs-paris-fc-1"
    },
    {
        "nom": "PSG vs RENNE",
        "url": "https://billetterie.psg.fr/fr/catalogue/match-foot-masculin-paris-vs-rennes-5"
    },
]

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
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            super().end_headers()
        
        def do_GET(self):
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
            # Sinon, servir depuis le dossier Site
            return super().do_GET()
        
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
    for match in MATCHS:
        verifier_match(match)

    pause = 90 + random.randint(0, 5)
    print(f"⏳ Pause {pause} secondes...")
    time.sleep(pause)


