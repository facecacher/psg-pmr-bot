import json
import os
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Chemins des fichiers
STATUS_FILE = 'status.json'
MATCHES_FILE = 'matches.json'
ANALYTICS_FILE = 'analytics.json'

# ====================
# ENDPOINTS BOT STATUS
# ====================

@app.route('/api/status', methods=['GET'])
def get_status():
    """Retourne le statut complet du bot depuis status.json"""
    try:
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Status file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ====================
# ENDPOINTS MATCHS
# ====================

@app.route('/api/matches', methods=['GET'])
def get_matches():
    """Liste tous les matchs surveillés"""
    try:
        with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        return jsonify(matches)
    except FileNotFoundError:
        # Si le fichier n'existe pas, le créer avec les matchs par défaut
        default_matches = [
            {
                "nom": "PSG vs PARIS FC",
                "url": "https://billetterie.psg.fr/fr/catalogue/match-foot-masculin-paris-sg-vs-paris-fc-1"
            },
            {
                "nom": "PSG vs RENNE",
                "url": "https://billetterie.psg.fr/fr/catalogue/match-foot-masculin-paris-vs-rennes-5"
            }
        ]
        with open(MATCHES_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_matches, f, ensure_ascii=False, indent=2)
        return jsonify(default_matches)

@app.route('/api/matches', methods=['POST'])
def add_match():
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
def delete_match(index):
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
def force_check(index):
    """Force la vérification d'un match spécifique"""
    # TODO: Implémenter la logique pour forcer une vérification
    return jsonify({"success": True, "message": "Vérification lancée"})

# ====================
# ENDPOINTS ANALYTICS
# ====================

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
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
def track_visitor():
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

# ====================
# ENDPOINTS BOT CONTROL
# ====================

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    """Arrête le bot"""
    # TODO: Implémenter l'arrêt du bot
    return jsonify({"success": True, "message": "Bot arrêté"})

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Démarre le bot"""
    # TODO: Implémenter le démarrage du bot
    return jsonify({"success": True, "message": "Bot démarré"})

@app.route('/api/bot/config', methods=['GET'])
def get_config():
    """Retourne la configuration du bot"""
    return jsonify({
        "check_interval": 90,
        "telegram_enabled": True,
        "debug_mode": False
    })

@app.route('/api/bot/config', methods=['PUT'])
def update_config():
    """Met à jour la configuration du bot"""
    data = request.json
    # TODO: Sauvegarder la config
    return jsonify({"success": True, "config": data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

