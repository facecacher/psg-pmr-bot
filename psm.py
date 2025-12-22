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
import collections

# ====================
# SYSTÈME DE LOGS POUR L'ADMIN
# ====================
backend_logs = collections.deque(maxlen=200)

def log(message, log_type='info'):
    """Log un message dans la console ET dans backend_logs"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Afficher dans la console
    print(message)
    
    # Stocker dans la liste
    backend_logs.append({
        'timestamp': timestamp,
        'type': log_type,
        'message': message
    })

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

# ====================
# HISTORIQUE DES DÉTECTIONS PMR
# ====================
DETECTIONS_HISTORY_FILE = 'detections_history.json'

def charger_historique_detections():
    """Charge l'historique des détections PMR"""
    try:
        if os.path.exists(DETECTIONS_HISTORY_FILE):
            with open(DETECTIONS_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log(f"⚠️ Erreur chargement historique: {e}", 'warning')
    return []

def sauvegarder_detection(match_nom, nb_places):
    """Sauvegarde une détection PMR dans l'historique"""
    try:
        historique = charger_historique_detections()
        detection = {
            "match": match_nom,
            "nb_places": nb_places,
            "date": datetime.now().isoformat(),
            "date_formatee": formater_date_francaise(datetime.now())
        }
        historique.append(detection)
        # Garder seulement les 50 dernières détections
        if len(historique) > 50:
            historique = historique[-50:]
        
        with open(DETECTIONS_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(historique, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"⚠️ Erreur sauvegarde détection: {e}", 'warning')

# Charger les matchs depuis le fichier JSON
def charger_matchs():
    try:
        with open('matches.json', 'r', encoding='utf-8') as f:
            matches = json.load(f)
        log(f"📂 matches.json chargé: {len(matches)} match(s)", 'info')
        return matches
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
        log(f"📂 matches.json créé avec {len(matchs_default)} match(s) par défaut", 'info')
        return matchs_default

# ====================
# FONCTIONS HELPER POUR GROQ
# ====================

def extract_teams_from_match_name(match_name):
    """Extrait les équipes depuis le nom du match"""
    # Format attendu: "PSG vs OM" ou "PSG vs PARIS FC"
    parts = match_name.split(' vs ')
    if len(parts) == 2:
        return {'home': parts[0].strip(), 'away': parts[1].strip()}
    return {'home': 'PSG', 'away': 'Adversaire'}

def detect_match_importance(home_team, away_team, match_name):
    """Détecte l'importance du match"""
    away_lower = away_team.lower()
    match_lower = match_name.lower()
    
    is_classico = 'classique' in match_lower or (home_team == 'PSG' and ('om' in away_lower or 'marseille' in away_lower))
    is_ol = 'lyon' in away_lower or 'ol' in away_lower
    is_monaco = 'monaco' in away_lower
    is_high_profile = is_classico or is_ol or is_monaco
    
    return {
        'is_classico': is_classico,
        'is_ol': is_ol,
        'is_monaco': is_monaco,
        'is_high_profile': is_high_profile,
        'rivalry': 'Le Classique' if is_classico else ('Grande affiche' if is_ol else ('Match attractif' if is_monaco else 'Match régulier'))
    }

def get_comparison_matches(match_name, home_team, limit=3):
    """Récupère les VRAIS autres matchs depuis matches.json pour la comparaison"""
    try:
        matches_data = charger_matchs()  # Utiliser la fonction existante
        
        # Filtrer les matchs : même équipe à domicile, exclure le match actuel
        comparison_matches = []
        for match in matches_data:
            match_nom = match.get('nom', '')
            # Vérifier que c'est un match à domicile de la même équipe
            if home_team in match_nom and match_nom != match_name:
                # Extraire l'équipe adverse
                parts = match_nom.split(' vs ')
                if len(parts) == 2 and parts[0].strip() == home_team:
                    away_team = parts[1].strip()
                    comparison_matches.append({
                        'name': match_nom,
                        'away_team': away_team,
                        'url': match.get('url', ''),
                        'key': f'match_{len(comparison_matches) + 1}'
                    })
        
        # Si pas assez de matchs réels, compléter avec des matchs estimés
        if len(comparison_matches) < limit:
            fallback_matches = [
                {'name': f'{home_team} vs Lyon', 'key': 'match_fallback_1'},
                {'name': f'{home_team} vs Monaco', 'key': 'match_fallback_2'},
                {'name': f'{home_team} vs Lens', 'key': 'match_fallback_3'}
            ]
            # Exclure ceux qui sont déjà dans comparison_matches
            for fallback in fallback_matches:
                if len(comparison_matches) >= limit:
                    break
                away_lower = fallback['name'].split(' vs ')[1].lower()
                if not any(away_lower in m['name'].lower() for m in comparison_matches):
                    if match_name.lower() not in fallback['name'].lower():
                        comparison_matches.append(fallback)
        
        return comparison_matches[:limit]
    except Exception as e:
        log(f"⚠️ Erreur récupération matchs de comparaison: {e}", 'warning')
        # Fallback avec matchs par défaut
        return [
            {'name': f'{home_team} vs Lyon', 'key': 'match_1'},
            {'name': f'{home_team} vs Monaco', 'key': 'match_2'},
            {'name': f'{home_team} vs Lens', 'key': 'match_3'}
        ]

# ====================
# SYSTÈME DE CACHE GROQ
# ====================
GROQ_CACHE_FILE = 'groq_cache.json'

def get_cached_groq_data(match_name):
    """Récupère les données en cache si elles existent et sont récentes (< 24h)"""
    try:
        with open(GROQ_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        if match_name in cache:
            cached_data = cache[match_name]
            last_updated = datetime.fromisoformat(cached_data.get('last_updated', '2000-01-01'))
            hours_diff = (datetime.now() - last_updated).total_seconds() / 3600
            
            if hours_diff < 24:
                log(f"✅ Données Groq en cache pour {match_name} ({hours_diff:.1f}h)", 'info')
                return cached_data
            else:
                log(f"⏰ Cache expiré pour {match_name} ({hours_diff:.1f}h)", 'info')
    except FileNotFoundError:
        pass
    except Exception as e:
        log(f"⚠️ Erreur lecture cache: {e}", 'warning')
    
    return None

def save_groq_cache(match_name, data):
    """Sauvegarde les données dans le cache"""
    try:
        cache = {}
        if os.path.exists(GROQ_CACHE_FILE):
            with open(GROQ_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        
        cache[match_name] = data
        cache[match_name]['last_updated'] = datetime.now().isoformat()
        
        with open(GROQ_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        
        log(f"💾 Cache Groq sauvegardé pour {match_name}", 'info')
    except Exception as e:
        log(f"⚠️ Erreur sauvegarde cache: {e}", 'warning')

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

            log(f"🌐 Chargement de {nom}...", 'info')
            try:
                page.goto(url, timeout=120000, wait_until="domcontentloaded")
                log(f"✅ Page chargée pour {nom}", 'success')
            except Exception as goto_error:
                log(f"⚠️ Erreur lors du chargement de la page pour {nom}: {goto_error}", 'warning')
                log(f"🔄 Nouvelle tentative...", 'info')
                page.goto(url, timeout=120000, wait_until="domcontentloaded")
                log(f"✅ Page chargée pour {nom} (2ème tentative)", 'success')
            
            # Attendre BEAUCOUP plus longtemps que le contenu se charge
            log(f"⏳ Attente du chargement complet...", 'info')
            page.wait_for_timeout(10000)  # 10 secondes au lieu de 4
            
            # Scroll AVANT de chercher les éléments
            log(f"📜 Scroll de la page...", 'info')
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
            log(f"{nom} → PMR trouvées : {len(pmr_elements)}", 'info')
            
            # Sauvegarder la détection si des PMR sont trouvées
            if len(pmr_elements) > 0:
                sauvegarder_detection(nom, len(pmr_elements))

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
                    log(f"{nom} → Pas de PMR (cooldown actif)", 'info')

            # Sauvegarder le status avant de fermer
            sauvegarder_status()

            context.close()
            browser.close()

    except Exception as e:
        log(f"⚠️ Erreur sur {nom} : {e}", 'error')
        import traceback
        log(f"📋 Détails de l'erreur :", 'error')
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
        nom = data.get('nom', '').strip()
        url = data.get('url', '').strip()
        
        # Validation
        if not nom or not url:
            return jsonify({"error": "Nom et URL requis"}), 400
        
        # Validation de l'URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return jsonify({"error": "URL invalide. Veuillez entrer une URL complète (ex: https://...)"}), 400
        except Exception:
            return jsonify({"error": "URL invalide"}), 400
        
        # Lire les matchs existants
        try:
            with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
                matches = json.load(f)
        except FileNotFoundError:
            matches = []
        
        # Vérifier si le match existe déjà
        for match in matches:
            if match.get('nom') == nom:
                return jsonify({"error": f"Un match avec le nom '{nom}' existe déjà"}), 409
            if match.get('url') == url:
                return jsonify({"error": f"Un match avec cette URL existe déjà"}), 409
        
        # Ajouter le nouveau match
        new_match = {"nom": nom, "url": url}
        matches.append(new_match)
        
        # Sauvegarder
        with open(MATCHES_FILE, 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        
        # Mettre à jour status.json immédiatement
        global MATCHS
        MATCHS = matches  # Mettre à jour la variable globale
        sauvegarder_status()  # Mettre à jour status.json pour que le site l'affiche
        
        log(f"✅ Match ajouté: {nom} ({url})", 'success')
        log(f"📊 Total de matchs surveillés: {len(matches)}", 'info')
        log(f"🔄 Le match sera vérifié au prochain cycle de surveillance (~90 secondes)", 'info')
        log(f"💾 matches.json mis à jour avec succès", 'success')
        log(f"💾 status.json mis à jour - le nouveau match apparaît sur le site public", 'success')
        
        return jsonify({"success": True, "match": new_match}), 201
    except Exception as e:
        print(f"❌ Erreur ajout match: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/matches/<int:index>', methods=['DELETE'])
def api_delete_match(index):
    """Supprime un match par son index"""
    try:
        with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        if 0 <= index < len(matches):
            deleted = matches.pop(index)
            
            # Sauvegarder
            with open(MATCHES_FILE, 'w', encoding='utf-8') as f:
                json.dump(matches, f, ensure_ascii=False, indent=2)
            
            # Mettre à jour status.json immédiatement
            global MATCHS
            MATCHS = matches  # Mettre à jour la variable globale
            sauvegarder_status()  # Mettre à jour status.json
            
            log(f"🗑️ Match supprimé: {deleted.get('nom')} ({deleted.get('url')})", 'error')
            log(f"📊 Matchs restants: {len(matches)}", 'info')
            log(f"💾 matches.json mis à jour avec succès", 'success')
            log(f"💾 status.json mis à jour - le site public reflète le changement", 'success')
            log(f"⏸️ Le match ne sera plus surveillé au prochain cycle", 'info')
            
            return jsonify({"success": True, "deleted": deleted})
        else:
            return jsonify({"error": "Index invalide"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/matches/<int:index>/check', methods=['POST'])
def api_force_check(index):
    """Force la vérification d'un match spécifique"""
    try:
        # Charger les matchs
        try:
            with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
                matches = json.load(f)
        except FileNotFoundError:
            matches = charger_matchs()
        
        # Vérifier que l'index est valide
        if 0 <= index < len(matches):
            match = matches[index]
            nom = match.get("nom", "Match inconnu")
            
            # Lancer la vérification dans un thread séparé pour ne pas bloquer
            def verifier_en_background():
                url_match = match.get("url", "URL inconnue")
                log(f"🔄 Vérification forcée de {nom}...", 'info')
                log(f"🌐 URL: {url_match}", 'info')
                verifier_match(match)
                log(f"✅ Vérification forcée de {nom} terminée", 'success')
            
            threading.Thread(target=verifier_en_background, daemon=True).start()
            
            return jsonify({
                "success": True, 
                "message": f"Vérification de {nom} lancée en arrière-plan"
            })
        else:
            return jsonify({"error": "Index invalide"}), 404
    except Exception as e:
        print(f"❌ Erreur vérification forcée: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics', methods=['GET'])
def api_get_analytics():
    """Retourne les statistiques du site web"""
    try:
        with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
            analytics = json.load(f)
        
        # S'assurer que toutes les propriétés existent
        default_values = {
            "visiteurs_totaux": 0,
            "visiteurs_en_ligne": 0,
            "visiteurs_aujourdhui": 0,
            "temps_moyen": "0m 0s",
            "taux_rebond": "0%",
            "clics_telegram": 0,
            "pic_connexions": 0,
            "taux_retour": "0%",
            "historique_7j": [0, 0, 0, 0, 0, 0, 0],
            "derniere_date": None
        }
        
        # Remplir les valeurs manquantes
        for key, default_value in default_values.items():
            if key not in analytics:
                analytics[key] = default_value
        
        # Vérifier si l'historique doit être mis à jour (nouveau jour)
        date_actuelle = datetime.now().strftime("%Y-%m-%d")
        derniere_date = analytics.get("derniere_date")
        
        if derniere_date != date_actuelle and derniere_date is not None:
            # Nouveau jour détecté, mettre à jour l'historique
            try:
                derniere_date_obj = datetime.strptime(derniere_date, "%Y-%m-%d")
                date_actuelle_obj = datetime.strptime(date_actuelle, "%Y-%m-%d")
                jours_ecoules = (date_actuelle_obj - derniere_date_obj).days
                
                if jours_ecoules > 0:
                    # Décaler l'historique
                    for i in range(min(jours_ecoules, 7)):
                        analytics["historique_7j"].pop(0)
                        analytics["historique_7j"].append(0)
                    
                    if jours_ecoules >= 7:
                        analytics["historique_7j"] = [0, 0, 0, 0, 0, 0, 0]
                    
                    analytics["visiteurs_aujourdhui"] = 0
                    analytics["derniere_date"] = date_actuelle
                    
                    # Sauvegarder la mise à jour
                    with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(analytics, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"⚠️ Erreur mise à jour historique: {e}")
        
        return jsonify(analytics)
    except FileNotFoundError:
        # Créer des stats par défaut (valeurs réelles, pas de simulation)
        default_analytics = {
            "visiteurs_totaux": 0,
            "visiteurs_en_ligne": 0,
            "visiteurs_aujourdhui": 0,
            "temps_moyen": "0m 0s",
            "taux_rebond": "0%",
            "clics_telegram": 0,
            "pic_connexions": 0,
            "taux_retour": "0%",
            "historique_7j": [0, 0, 0, 0, 0, 0, 0],
            "derniere_date": datetime.now().strftime("%Y-%m-%d")
        }
        with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_analytics, f, ensure_ascii=False, indent=2)
        return jsonify(default_analytics)
    except Exception as e:
        print(f"❌ Erreur lecture analytics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/visitor', methods=['POST'])
def api_track_visitor():
    """Enregistre une visite sur le site"""
    try:
        # Charger analytics
        try:
            with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                analytics = json.load(f)
        except FileNotFoundError:
            # Initialiser avec toutes les propriétés nécessaires
            analytics = {
                "visiteurs_totaux": 0,
                "visiteurs_en_ligne": 0,
                "visiteurs_aujourdhui": 0,
                "temps_moyen": "0m 0s",
                "taux_rebond": "0%",
                "clics_telegram": 0,
                "pic_connexions": 0,
                "taux_retour": "0%",
                "historique_7j": [0, 0, 0, 0, 0, 0, 0],
                "derniere_date": None
            }
        
        # S'assurer que toutes les propriétés existent
        if "visiteurs_totaux" not in analytics:
            analytics["visiteurs_totaux"] = 0
        if "visiteurs_en_ligne" not in analytics:
            analytics["visiteurs_en_ligne"] = 0
        if "visiteurs_aujourdhui" not in analytics:
            analytics["visiteurs_aujourdhui"] = 0
        if "temps_moyen" not in analytics:
            analytics["temps_moyen"] = "0m 0s"
        if "taux_rebond" not in analytics:
            analytics["taux_rebond"] = "0%"
        if "clics_telegram" not in analytics:
            analytics["clics_telegram"] = 0
        if "pic_connexions" not in analytics:
            analytics["pic_connexions"] = 0
        if "taux_retour" not in analytics:
            analytics["taux_retour"] = "0%"
        if "historique_7j" not in analytics:
            analytics["historique_7j"] = [0, 0, 0, 0, 0, 0, 0]
        if "derniere_date" not in analytics:
            analytics["derniere_date"] = None
        
        # Obtenir la date actuelle (format YYYY-MM-DD)
        date_actuelle = datetime.now().strftime("%Y-%m-%d")
        derniere_date = analytics.get("derniere_date")
        
        # Si c'est un nouveau jour, mettre à jour l'historique
        if derniere_date != date_actuelle:
            if derniere_date is not None:
                # Calculer le nombre de jours écoulés
                try:
                    derniere_date_obj = datetime.strptime(derniere_date, "%Y-%m-%d")
                    date_actuelle_obj = datetime.strptime(date_actuelle, "%Y-%m-%d")
                    jours_ecoules = (date_actuelle_obj - derniere_date_obj).days
                    
                    # Si plus d'un jour s'est écoulé, décaler l'historique
                    if jours_ecoules > 0:
                        # Décaler l'historique vers la gauche
                        for i in range(min(jours_ecoules, 7)):
                            analytics["historique_7j"].pop(0)
                            analytics["historique_7j"].append(0)
                        
                        # Si plus de 7 jours, réinitialiser
                        if jours_ecoules >= 7:
                            analytics["historique_7j"] = [0, 0, 0, 0, 0, 0, 0]
                except Exception as e:
                    print(f"⚠️ Erreur calcul jours: {e}")
                    # En cas d'erreur, réinitialiser l'historique
                    analytics["historique_7j"] = [0, 0, 0, 0, 0, 0, 0]
            
            # Réinitialiser le compteur du jour actuel
            analytics["visiteurs_aujourdhui"] = 0
            analytics["derniere_date"] = date_actuelle
        
        # Incrémenter les compteurs
        analytics["visiteurs_totaux"] = analytics.get("visiteurs_totaux", 0) + 1
        analytics["visiteurs_en_ligne"] = analytics.get("visiteurs_en_ligne", 0) + 1
        analytics["visiteurs_aujourdhui"] = analytics.get("visiteurs_aujourdhui", 0) + 1
        
        # Mettre à jour l'historique des 7 derniers jours (dernier élément = aujourd'hui)
        if len(analytics["historique_7j"]) > 0:
            analytics["historique_7j"][-1] = analytics["visiteurs_aujourdhui"]
        else:
            analytics["historique_7j"] = [analytics["visiteurs_aujourdhui"]]
        
        # Mettre à jour le pic de connexions si nécessaire
        if analytics["visiteurs_en_ligne"] > analytics.get("pic_connexions", 0):
            analytics["pic_connexions"] = analytics["visiteurs_en_ligne"]
        
        # Sauvegarder
        with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(analytics, f, ensure_ascii=False, indent=2)
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Erreur tracking visiteur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/detections-history', methods=['GET'])
def api_get_detections_history():
    """Retourne l'historique des détections PMR"""
    try:
        historique = charger_historique_detections()
        # Filtrer par match si spécifié
        match_filter = request.args.get('match')
        if match_filter:
            historique = [d for d in historique if match_filter.lower() in d.get('match', '').lower()]
        return jsonify(historique)
    except Exception as e:
        log(f"❌ Erreur récupération historique: {e}", 'error')
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
            # Initialiser avec toutes les propriétés nécessaires
            analytics = {
                "visiteurs_totaux": 0,
                "visiteurs_en_ligne": 0,
                "visiteurs_aujourdhui": 0,
                "temps_moyen": "0m 0s",
                "taux_rebond": "0%",
                "clics_telegram": 0,
                "pic_connexions": 0,
                "taux_retour": "0%",
                "historique_7j": [0, 0, 0, 0, 0, 0, 0]
            }
        
        # S'assurer que toutes les propriétés existent
        if "clics_telegram" not in analytics:
            analytics["clics_telegram"] = 0
        
        # Incrémenter
        analytics["clics_telegram"] = analytics.get("clics_telegram", 0) + 1
        
        # Sauvegarder
        with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(analytics, f, ensure_ascii=False, indent=2)
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Erreur tracking clic Telegram: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def api_get_logs():
    """Retourne les logs du backend"""
    try:
        limit = request.args.get('limit', 50, type=int)
        logs = list(backend_logs)[-limit:]  # Derniers N logs
        return jsonify({
            "success": True,
            "logs": logs,
            "total": len(backend_logs)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/groq/analyze', methods=['GET'])
def api_groq_analyze():
    """Génère une analyse IA complète du match avec Groq (analysis, comparison, weather, lineups)"""
    try:
        match_name = request.args.get('match')
        if not match_name:
            return jsonify({"error": "Paramètre 'match' requis"}), 400
        
        # Vérifier le cache d'abord
        cached_data = get_cached_groq_data(match_name)
        if cached_data:
            return jsonify(cached_data)
        
        # Charger les données du match depuis status.json
        try:
            with open('status.json', 'r', encoding='utf-8') as f:
                status = json.load(f)
        except FileNotFoundError:
            return jsonify({"error": "status.json non trouvé"}), 404
        
        match = next((m for m in status.get('matchs', []) if m['nom'] == match_name), None)
        if not match:
            return jsonify({"error": "Match non trouvé"}), 404
        
        # Extraire les équipes
        teams = extract_teams_from_match_name(match_name)
        home_team = teams['home']
        away_team = teams['away']
        
        # Détecter l'importance
        importance = detect_match_importance(home_team, away_team, match_name)
        
        # Récupérer les VRAIS matchs de comparaison depuis matches.json
        comparison_matches = get_comparison_matches(match_name, home_team, limit=3)
        
        # Date du match (utiliser date actuelle)
        match_date = datetime.now()
        date_formatted = match_date.strftime("%d %B %Y")
        
        # Construire la section comparaison
        if comparison_matches:
            comparison_section = f"""
2. COMPARAISON AVEC AUTRES MATCHS DE {home_team}:
   
   Analyse ET compare "{match_name}" avec ces matchs RÉELS du calendrier :
   
   {chr(10).join([f'   {i+1}. {m["name"]}' for i, m in enumerate(comparison_matches)])}
   
   Pour CHAQUE match ci-dessus, analyse son importance et donne un score d'anticipation (0-100).
   Règles:
   - {home_team}-OM (Le Classique) = toujours le plus haut (90-100)
   - {home_team}-Lyon = très attractif (80-92)
   - {home_team}-Monaco = attractif (75-88)
   - Autres équipes = variable selon classement (60-80)
   
   Compare "{match_name}" avec ces matchs et classe-les par importance.
   Retourne les scores pour:
   - current_match: score de "{match_name}"
   {chr(10).join([f'   - {m["key"]}: score de "{m["name"]}"' for m in comparison_matches])}
"""
        else:
            comparison_section = f"""
2. COMPARAISON AVEC AUTRES MATCHS:
   Génère des scores estimés pour 3 autres matchs importants de {home_team}:
   - match_1: {home_team} vs Lyon (grand rival)
   - match_2: {home_team} vs Monaco (affiche attractive)
   - match_3: {home_team} vs Lens (match moyen)
"""
        
        # Construire les parties du prompt qui contiennent des backslashes
        psg_lineup_text = '- Utilise les vrais joueurs du PSG actuel: Donnarumma (GK), Hakimi, Marquinhos (C), Skriniar, Mendes (DF), Vitinha, Zaïre-Emery, Ugarte (MF), Dembélé, Ramos, Barcola (FW)'
        om_lineup_text = "- Utilise les vrais joueurs de l'OM actuel: López (GK), Clauss, Gigot, Balerdi, Tavares (DF), Rongier, Veretout, Harit (MF), Aubameyang, Greenwood, Moumbagna (FW)"
        
        home_lineup_instruction = psg_lineup_text if home_team == 'PSG' else f'- Utilise les vrais joueurs actuels de {home_team}'
        away_lineup_instruction = om_lineup_text if ('OM' in away_team or 'Marseille' in away_team) else f'- Utilise les vrais joueurs actuels de {away_team}'
        
        # Construire la partie comparaison (sans backslash dans les expressions)
        comparison_json_lines = []
        comparison_name_lines = []
        if comparison_matches:
            for m in comparison_matches:
                comparison_json_lines.append(f'    "{m["key"]}": number,')
                comparison_name_lines.append(f'    "{m["key"]}_name": "{m["name"]}",')
        else:
            comparison_json_lines = ['    "match_1": number,', '    "match_2": number,', '    "match_3": number,']
        
        # Construire les chaînes de comparaison
        comparison_json_str = '\n'.join(comparison_json_lines)
        comparison_name_str = '\n'.join(comparison_name_lines) if comparison_name_lines else ''
        
        # Construire les parties du prompt avec des conditions
        importance_text = 'Match à très forte affluence' if importance['is_high_profile'] else 'Match d\'importance moyenne'
        classico_text = 'Le Classique PSG-OM génère toujours une demande exceptionnelle (90-100%).' if importance['is_classico'] else ''
        ol_text = 'PSG-OL est une affiche majeure de Ligue 1 (80-95%).' if importance['is_ol'] else ''
        monaco_text = 'PSG-Monaco est un match attractif (75-90%).' if importance['is_monaco'] else ''
        other_text = 'Pour un match moins médiatisé, ajuste les scores en conséquence (60-85%).' if not importance['is_high_profile'] else ''
        
        # Construire le template JSON séparément
        json_template = """{{
  "analysis": {{
    "hype_score": number,
    "affluence_prevue": number,
    "probabilite_pmr": number,
    "analyse": "string adaptée à """ + match_name + """"
  }},
  "comparison": {{
    "current_match": number,
""" + comparison_json_str + """
""" + comparison_name_str + """
  }},
  "weather": {{
    "temperature": number,
    "condition": "string",
    "rain_chance": number,
    "wind_speed": number,
    "emoji": "string"
  }},
  "lineups": {{
    "home": {{
      "formation": "string",
      "gk": ["string"],
      "df": ["string", "string", "string", "string"],
      "mf": ["string", "string", "string"],
      "fw": ["string", "string", "string"]
    }},
    "away": {{
      "formation": "string",
      "gk": ["string"],
      "df": ["string", "string", "string", "string"],
      "mf": ["string", "string", "string"],
      "fw": ["string", "string", "string"]
    }}
  }}
}}"""
        
        # Construire le prompt complet en concaténant les parties
        prompt = f"""Tu es un expert en football français, météorologie et analyse de données sportives.

MATCH À ANALYSER:
- Équipes: {match_name}
- Compétition: Ligue 1
- Date: {date_formatted}
- Stade: Parc des Princes
- Contexte: {importance['rivalry']}
- Importance: {importance_text}
- Nombre de vérifications: {match.get('nb_checks', 0)}
- Statut PMR actuel: {'Disponible' if match.get('pmr_disponible', False) else 'Non disponible'}

CONSIGNES D'ANALYSE DÉTAILLÉE:

1. ANALYSE D'ANTICIPATION APPROFONDIE:
   Analyse en profondeur le niveau d'attente pour ce match spécifique "{match_name}".
   {classico_text}
   {ol_text}
   {monaco_text}
   {other_text}
   
   - hype_score: niveau d'anticipation supporters (0-100) - Justifie avec des éléments concrets
   - affluence_prevue: taux de remplissage estimé (0-100) - Base-toi sur l'historique du Parc des Princes
   - probabilite_pmr: chance qu'une place PMR se libère (0-100) - Considère la rareté des places PMR
   - analyse: explication DÉTAILLÉE (5-7 phrases) incluant:
     * Contexte du match (rivalité, enjeux, importance)
     * Historique des places PMR pour ce type de match
     * Facteurs influençant la disponibilité (demande, timing, saison)
     * Recommandations concrètes pour l'utilisateur
     * Probabilité détaillée avec justification

{comparison_section}

3. MÉTÉO PRÉVUE DÉTAILLÉE:
   Pour Parc des Princes le {date_formatted}:
   - Utilise des données météo réalistes pour Paris/France à cette période
   - En janvier: généralement 5-10°C, souvent nuageux, risque de pluie moyen
   - En été: 20-30°C, plutôt ensoleillé
   - Adapte selon la saison réelle
   
   - temperature: température en °C (cohérente avec la date)
   - condition: description détaillée ("Ensoleillé avec quelques nuages", "Nuageux avec averses possibles", etc.)
   - rain_chance: probabilité de pluie (0-100) avec justification
   - wind_speed: vitesse vent en km/h (10-20 km/h typique)
   - emoji: emoji météo approprié (☀️, 🌤️, ⛅, 🌧️, ⛈️, etc.)

4. COMPOSITIONS PROBABLES DÉTAILLÉES:
   Génère les compositions RÉALISTES et ACTUELLES (saison 2024-2025):
   
   Pour {home_team}:
   {home_lineup_instruction}
   - Formation: 4-3-3 (typique) ou autre selon le contexte
   - Inclus les vrais noms de joueurs actuels
   
   Pour {away_team}:
   {away_lineup_instruction}
   - Formation: 4-3-3 ou autre selon le contexte
   - Inclus les vrais noms de joueurs actuels

IMPORTANT:
- Analyse TRÈS DÉTAILLÉE avec justification de chaque score
- Adapte TOUS les scores et analyses au match spécifique "{match_name}"
- Ne copie pas les valeurs d'un autre match
- Sois cohérent: PSG-OM > PSG-OL > PSG-Monaco > PSG-équipe moyenne
- Utilise les vrais effectifs 2024-2025 avec noms réels
- Météo réaliste et détaillée pour {date_formatted}
- L'analyse doit faire 5-7 phrases minimum avec détails concrets

Réponds UNIQUEMENT avec ce JSON, sans texte avant/après, sans markdown:
""" + json_template

        # Clé API Groq (doit être définie dans les variables d'environnement)
        GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        if not GROQ_API_KEY:
            log("⚠️ GROQ_API_KEY non définie, impossible de générer l'analyse", 'warning')
            return jsonify({"error": "GROQ_API_KEY non configurée"}), 500
        
        GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
        
        log(f"📡 Appel API Groq pour {match_name}", 'info')
        log(f"🔑 GROQ_API_KEY présente: {'Oui' if GROQ_API_KEY else 'Non'}", 'info')
        log(f"🔗 URL API: {GROQ_API_URL}", 'info')
        
        # Appeler l'API Groq
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": "Tu es un expert en football français, météorologie et analyse de données sportives. Réponds UNIQUEMENT avec du JSON valide, sans markdown, sans code blocks."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.4,
            "max_tokens": 1500,
            "top_p": 0.9
        }
        
        log(f"📤 Payload envoyé - Model: {payload['model']}, Messages: {len(payload['messages'])}", 'info')
        log(f"📝 Taille du prompt: {len(prompt)} caractères", 'info')
        
        try:
            response = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=30)
            log(f"📥 Réponse Groq reçue - Status: {response.status_code}", 'info')
        except requests.exceptions.Timeout:
            log(f"⏱️ Timeout lors de l'appel API Groq (30s dépassé)", 'error')
            raise
        except requests.exceptions.RequestException as e:
            log(f"❌ Erreur réseau lors de l'appel API Groq: {e}", 'error')
            raise
        
        if response.status_code != 200:
            error_detail = ""
            try:
                error_response = response.json()
                error_detail = f" - {error_response.get('error', {}).get('message', str(error_response))}"
            except:
                error_detail = f" - {response.text[:500]}"
            log(f"❌ Erreur API Groq: {response.status_code}{error_detail}", 'error')
            log(f"📄 Réponse complète (premiers 1000 caractères): {response.text[:1000]}", 'error')
            # Retourner des données par défaut au lieu d'une erreur 500
            default_data = {
                "analysis": {
                    "hype_score": 75,
                    "affluence_prevue": 85,
                    "probabilite_pmr": 15,
                    "analyse": f"Le match {match_name} a été vérifié {match.get('nb_checks', 0)} fois. Basé sur l'historique, la probabilité de disponibilité de places PMR est modérée. Recommandation : activer les alertes Telegram pour ne pas manquer une opportunité."
                },
                "comparison": {
                    "current_match": 75,
                    "match_1": 70,
                    "match_1_name": comparison_matches[0]['name'] if comparison_matches else f"{home_team} vs Lyon",
                    "match_2": 65,
                    "match_2_name": comparison_matches[1]['name'] if len(comparison_matches) > 1 else f"{home_team} vs Monaco",
                    "match_3": 60,
                    "match_3_name": comparison_matches[2]['name'] if len(comparison_matches) > 2 else f"{home_team} vs Lens"
                },
                "weather": {
                    "temperature": 12,
                    "condition": "Variable",
                    "rain_chance": 30,
                    "wind_speed": 15,
                    "emoji": "🌤️"
                },
                "lineups": {
                    "home": {
                        "formation": "4-3-3",
                        "gk": ["Gardien"],
                        "df": ["DF1", "DF2", "DF3", "DF4"],
                        "mf": ["MF1", "MF2", "MF3"],
                        "fw": ["FW1", "FW2", "FW3"]
                    },
                    "away": {
                        "formation": "4-3-3",
                        "gk": ["Gardien"],
                        "df": ["DF1", "DF2", "DF3", "DF4"],
                        "mf": ["MF1", "MF2", "MF3"],
                        "fw": ["FW1", "FW2", "FW3"]
                    }
                },
                "last_updated": datetime.now().isoformat(),
                "error": True
            }
            save_groq_cache(match_name, default_data)
            return jsonify(default_data)
        
        result = response.json()
        log(f"✅ Réponse JSON parsée avec succès", 'info')
        log(f"📊 Nombre de choix: {len(result.get('choices', []))}", 'info')
        
        if 'choices' not in result or len(result['choices']) == 0:
            raise ValueError("Aucun choix dans la réponse Groq")
        
        content = result['choices'][0]['message']['content']
        content_original = content  # Sauvegarder pour les logs d'erreur
        log(f"📝 Contenu brut reçu (premiers 500 caractères): {content[:500]}", 'info')
        log(f"📏 Taille du contenu: {len(content)} caractères", 'info')
        
        # Parser le JSON de la réponse
        try:
            # Nettoyer le contenu (enlever markdown si présent)
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Extraire le JSON
            json_match = None
            if '{' in content:
                start = content.find('{')
                end = content.rfind('}') + 1
                json_match = content[start:end]
            
            if not json_match:
                raise ValueError("Aucun JSON trouvé dans la réponse")
            
            complete_data = json.loads(json_match)
            
            # Vérifier que toutes les sections sont présentes
            if not all(key in complete_data for key in ['analysis', 'comparison', 'weather', 'lineups']):
                raise ValueError("Données incomplètes dans la réponse Groq")
            
            # Ajouter timestamp
            complete_data['last_updated'] = datetime.now().isoformat()
            
            # Logger la réponse Groq complète de manière structurée
            log(f"✅ Réponse Groq reçue pour {match_name}", 'info')
            
            # Logger chaque section séparément pour plus de lisibilité
            if 'analysis' in complete_data:
                analysis = complete_data['analysis']
                log(f"📊 Analyse IA - Hype: {analysis.get('hype_score', 'N/A')}% | Affluence: {analysis.get('affluence_prevue', 'N/A')}% | Probabilité PMR: {analysis.get('probabilite_pmr', 'N/A')}%", 'info')
                log(f"💭 Analyse détaillée: {analysis.get('analyse', 'N/A')[:200]}...", 'info')
            
            if 'comparison' in complete_data:
                comp = complete_data['comparison']
                log(f"📈 Comparaison - Match actuel: {comp.get('current_match', 'N/A')}%", 'info')
            
            if 'weather' in complete_data:
                weather = complete_data['weather']
                log(f"🌤️ Météo - {weather.get('temperature', 'N/A')}°C | {weather.get('condition', 'N/A')} | Pluie: {weather.get('rain_chance', 'N/A')}% | Vent: {weather.get('wind_speed', 'N/A')} km/h", 'info')
            
            if 'lineups' in complete_data:
                lineups = complete_data['lineups']
                home_form = lineups.get('home', {}).get('formation', 'N/A')
                away_form = lineups.get('away', {}).get('formation', 'N/A')
                log(f"⚽ Compositions - Domicile: {home_form} | Extérieur: {away_form}", 'info')
            
            # Logger le JSON complet pour référence (formaté)
            log(f"📋 JSON Groq complet:\n{json.dumps(complete_data, ensure_ascii=False, indent=2)}", 'info')
            
            # Sauvegarder dans le cache
            save_groq_cache(match_name, complete_data)
            
            return jsonify(complete_data)
            
        except (json.JSONDecodeError, ValueError) as e:
            # Si le parsing échoue, retourner des données par défaut
            log(f"⚠️ Réponse Groq invalide, utilisation de valeurs par défaut: {e}", 'warning')
            log(f"📄 Contenu original (premiers 1000 caractères): {content_original[:1000]}", 'warning')
            log(f"📄 Contenu nettoyé (premiers 1000 caractères): {content[:1000]}", 'warning')
            if json_match:
                log(f"📄 JSON extrait (premiers 1000 caractères): {json_match[:1000]}", 'warning')
            default_data = {
                "analysis": {
                    "hype_score": 75,
                    "affluence_prevue": 85,
                    "probabilite_pmr": 15,
                    "analyse": f"Le match {match_name} a été vérifié {match.get('nb_checks', 0)} fois. Basé sur l'historique, la probabilité de disponibilité de places PMR est modérée. Recommandation : activer les alertes Telegram pour ne pas manquer une opportunité."
                },
                "comparison": {
                    "current_match": 75,
                    "match_1": 70,
                    "match_1_name": comparison_matches[0]['name'] if comparison_matches else f"{home_team} vs Lyon",
                    "match_2": 65,
                    "match_2_name": comparison_matches[1]['name'] if len(comparison_matches) > 1 else f"{home_team} vs Monaco",
                    "match_3": 60,
                    "match_3_name": comparison_matches[2]['name'] if len(comparison_matches) > 2 else f"{home_team} vs Lens"
                },
                "weather": {
                    "temperature": 12,
                    "condition": "Variable",
                    "rain_chance": 30,
                    "wind_speed": 15,
                    "emoji": "🌤️"
                },
                "lineups": {
                    "home": {
                        "formation": "4-3-3",
                        "gk": ["Gardien"],
                        "df": ["DF1", "DF2", "DF3", "DF4"],
                        "mf": ["MF1", "MF2", "MF3"],
                        "fw": ["FW1", "FW2", "FW3"]
                    },
                    "away": {
                        "formation": "4-3-3",
                        "gk": ["Gardien"],
                        "df": ["DF1", "DF2", "DF3", "DF4"],
                        "mf": ["MF1", "MF2", "MF3"],
                        "fw": ["FW1", "FW2", "FW3"]
                    }
                },
                "last_updated": datetime.now().isoformat(),
                "error": True
            }
            save_groq_cache(match_name, default_data)
            return jsonify(default_data)
            
    except Exception as e:
        log(f"❌ Erreur analyse Groq: {e}", 'error')
        import traceback
        traceback.print_exc()
        # Retourner des données par défaut au lieu d'une erreur 500
        try:
            match_name = request.args.get('match', 'Match inconnu')
            teams = extract_teams_from_match_name(match_name)
            home_team = teams['home']
            comparison_matches = get_comparison_matches(match_name, home_team, limit=3)
        except:
            home_team = 'PSG'
            comparison_matches = []
        
        default_data = {
            "analysis": {
                "hype_score": 75,
                "affluence_prevue": 85,
                "probabilite_pmr": 15,
                "analyse": f"Erreur lors de la génération de l'analyse IA. Données par défaut affichées."
            },
            "comparison": {
                "current_match": 75,
                "match_1": 70,
                "match_1_name": comparison_matches[0]['name'] if comparison_matches else f"{home_team} vs Lyon",
                "match_2": 65,
                "match_2_name": comparison_matches[1]['name'] if len(comparison_matches) > 1 else f"{home_team} vs Monaco",
                "match_3": 60,
                "match_3_name": comparison_matches[2]['name'] if len(comparison_matches) > 2 else f"{home_team} vs Lens"
            },
            "weather": {
                "temperature": 12,
                "condition": "Variable",
                "rain_chance": 30,
                "wind_speed": 15,
                "emoji": "🌤️"
            },
            "lineups": {
                "home": {
                    "formation": "4-3-3",
                    "gk": ["Gardien"],
                    "df": ["DF1", "DF2", "DF3", "DF4"],
                    "mf": ["MF1", "MF2", "MF3"],
                    "fw": ["FW1", "FW2", "FW3"]
                },
                "away": {
                    "formation": "4-3-3",
                    "gk": ["Gardien"],
                    "df": ["DF1", "DF2", "DF3", "DF4"],
                    "mf": ["MF1", "MF2", "MF3"],
                    "fw": ["FW1", "FW2", "FW3"]
                }
            },
            "last_updated": datetime.now().isoformat(),
            "error": True
        }
        return jsonify(default_data)

def start_flask_api():
    """Démarre l'API Flask dans un thread séparé"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# Démarrer l'API Flask en arrière-plan
threading.Thread(target=start_flask_api, daemon=True).start()
log("🔌 API Flask démarrée sur le port 5000", 'success')

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
    log(f"🌐 Serveur web démarré sur le port {port}", 'success')
    log(f"📱 Site accessible sur http://localhost:{port}/index.html", 'info')
    server.serve_forever()

# Lancer le serveur web en arrière-plan
threading.Thread(target=start_web_server, daemon=True).start()

log("🚀 Bot PSM démarré avec serveur web intégré!", 'success')

# ✅ BOUCLE PRINCIPALE MULTI-MATCHS
while True:
    MATCHS = charger_matchs()  # Recharger les matchs à chaque itération
    log(f"📋 Cycle de surveillance: {len(MATCHS)} match(s) à vérifier", 'info')
    if len(MATCHS) > 0:
        matchs_noms = ', '.join([m['nom'] for m in MATCHS])
        log(f"📝 Matchs: {matchs_noms}", 'info')
    for match in MATCHS:
        verifier_match(match)

    pause = 90 + random.randint(0, 5)
    log(f"⏳ Pause {pause} secondes...", 'info')
    time.sleep(pause)


