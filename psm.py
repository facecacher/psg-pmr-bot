from playwright.sync_api import sync_playwright
import requests
import time
from datetime import datetime, timedelta
import random
import os

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

def envoyer_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        r = requests.post(url, data=data, timeout=10)
        print("Telegram:", r.text)
    except Exception as e:
        print("Erreur Telegram:", e)

def verifier_match(match):
    nom = match["nom"]
    url = match["url"]

    if nom not in dernier_message_indispo:
        dernier_message_indispo[nom] = datetime.now() - timedelta(hours=8)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,  # Mode invisible, fonctionne sans écran
                args=[
                    '--no-sandbox',  # Permissions Docker
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',  # Évite les problèmes de mémoire
                    '--disable-gpu',  # Pas de carte graphique nécessaire
                    '--window-size=1920x1080'
                ]
            )
            
            # Ajouter un contexte pour éviter la détection
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = context.new_page()  # Au lieu de browser.new_page()

            page.goto(url, timeout=60000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(4000)

            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(2000)

            heure = datetime.now().strftime("%H:%M:%S")

            pmr_elements = page.query_selector_all('div[data-offer-type="PMR"]')
            print(f"{nom} → PMR trouvées :", len(pmr_elements))

            if len(pmr_elements) > 0:
                envoyer_message(f"✅ [{heure}] PLACE PMR DISPONIBLE POUR {nom}")
            else:
                if datetime.now() - dernier_message_indispo[nom] >= timedelta(hours=8):
                    envoyer_message(f"❌ [{heure}] TOUJOURS PAS DE PLACE PMR POUR {nom}")
                    dernier_message_indispo[nom] = datetime.now()
                else:
                    print(f"{nom} → Pas de PMR (cooldown actif)")

            context.close()
            browser.close()

    except Exception as e:
        print(f"⚠️ Erreur sur {nom} :", e)

# ✅ BOUCLE PRINCIPALE MULTI-MATCHS
while True:
    for match in MATCHS:
        verifier_match(match)

    pause = 90 + random.randint(0, 5)
    print(f"⏳ Pause {pause} secondes...")
    time.sleep(pause)


