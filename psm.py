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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

# Vérification des variables d'environnement
if not TELEGRAM_TOKEN:
    print("❌ ERREUR: TELEGRAM_TOKEN n'est pas défini!")
    print("💡 Vérifiez que la variable d'environnement TELEGRAM_TOKEN est configurée dans Dokploy")
    import sys
    sys.exit(1)
if not CHAT_ID:
    print("❌ ERREUR: TELEGRAM_CHAT_ID n'est pas défini!")
    print("💡 Vérifiez que la variable d'environnement TELEGRAM_CHAT_ID est configurée dans Dokploy")
    import sys
    sys.exit(1)

print("🚀 Bot PSM démarré!")
print(f"📋 Mode headless: {HEADLESS}")
print(f"📊 Nombre de matchs à surveiller: {len(MATCHS)}")

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
            browser = p.chromium.launch(headless=HEADLESS)
            page = browser.new_page()

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

            browser.close()

    except Exception as e:
        print(f"⚠️ Erreur sur {nom} :", e)

# ✅ BOUCLE PRINCIPALE MULTI-MATCHS
print("🔄 Démarrage de la surveillance...")
import sys
try:
    while True:
        for match in MATCHS:
            verifier_match(match)

        pause = 90 + random.randint(0, 5)
        print(f"⏳ Pause {pause} secondes...")
        sys.stdout.flush()  # Force l'affichage des logs
        time.sleep(pause)
except KeyboardInterrupt:
    print("🛑 Arrêt demandé par l'utilisateur")
except Exception as e:
    print(f"💥 ERREUR FATALE: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


