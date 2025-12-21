from playwright.sync_api import sync_playwright
import requests
import time
from datetime import datetime, timedelta
import random
import json
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

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
        "derniere_mise_a_jour": datetime.now().strftime("%d/%m/%Y à %H:%M:%S"),
        "matchs": []
    }
    
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
        
        status["matchs"].append({
            "nom": nom,
            "url": match["url"],
            "pmr_disponible": pmr_dispo,
            "dernier_check": dernier_check_str,
            "nb_checks": nb_checks
        })
    
    with open('status.json', 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

def verifier_match(match):
    nom = match["nom"]
    url = match["url"]

    if nom not in dernier_message_indispo:
        dernier_message_indispo[nom] = datetime.now() - timedelta(hours=8)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--window-size=1920x1080',
                    '--disable-blink-features=AutomationControlled'
                ]
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
            page.goto(url, timeout=120000, wait_until="domcontentloaded")
            print(f"✅ Page chargée pour {nom}")
            
            # Attendre que la page soit prête avec un timeout plus long
            try:
                page.wait_for_load_state("networkidle", timeout=60000)
            except:
                print(f"⚠️ Timeout networkidle pour {nom}, on continue quand même...")
            
            page.wait_for_timeout(4000)

            # Scroll progressif
            for i in range(3):
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(1000)

            heure = datetime.now().strftime("%H:%M:%S")

            pmr_elements = page.query_selector_all('div[data-offer-type="PMR"]')
            print(f"{nom} → PMR trouvées :", len(pmr_elements))

            # Mettre à jour les statistiques
            nb_checks_par_match[nom] = nb_checks_par_match.get(nom, 0) + 1
            dernier_check_par_match[nom] = datetime.now()
            pmr_disponible_par_match[nom] = len(pmr_elements) > 0

            if len(pmr_elements) > 0:
                envoyer_message(f"✅ [{heure}] PLACE PMR DISPONIBLE POUR {nom}")
            else:
                if datetime.now() - dernier_message_indispo[nom] >= timedelta(hours=8):
                    envoyer_message(f"❌ [{heure}] TOUJOURS PAS DE PLACE PMR POUR {nom}")
                    dernier_message_indispo[nom] = datetime.now()
                else:
                    print(f"{nom} → Pas de PMR (cooldown actif)")

            # Sauvegarder le status avant de fermer
            sauvegarder_status()

            context.close()
            browser.close()

    except Exception as e:
        print(f"⚠️ Erreur sur {nom} :", e)

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
                # status.json est dans /app (WORKDIR)
                status_path = '/app/status.json'
                if os.path.exists(status_path):
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    with open(status_path, 'rb') as f:
                        self.wfile.write(f.read())
                    return
                else:
                    self.send_response(404)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'status.json not found')
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


