
from flask import Flask, request, jsonify
import os
import krakenex
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

api = krakenex.API()
api.key = os.getenv("KRAKEN_API_KEY")
api.secret = os.getenv("KRAKEN_API_SECRET")

# Mémoire d'état par stratégie / compte / plateforme
position_status = {}

def get_available_balance(currency="ZCAD"):
    try:
        balance = api.query_private("Balance")
        return float(balance["result"].get(currency, 0))
    except Exception as e:
        print("Erreur récupération solde :", e)
        return 0

def place_market_order(pair, volume):
    try:
        response = api.query_private("AddOrder", {
            "pair": pair,
            "type": "buy",
            "ordertype": "market",
            "volume": str(volume)
        })
        return response
    except Exception as e:
        return {"error": str(e)}

@app.route("/", methods=["GET"])
def home():
    return "Bot Env24 multi-niveau en ligne 🚀"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if not data:
        return jsonify({"error": "No data received"}), 400

    strategy = data.get("strategy")
    platform = data.get("platform")
    account = data.get("account")
    symbol = data.get("symbol", "BTC/CAD").replace("/", "")
    signal = data.get("signal")

    if strategy != "Env24" or platform != "Kraken":
        return jsonify({"status": "Ignored: strategy or platform mismatch"}), 200

    # Initialiser l'état si non existant
    if account not in position_status:
        position_status[account] = {}
    if symbol not in position_status[account]:
        position_status[account][symbol] = {"status": "none"}

    current_status = position_status[account][symbol]["status"]

    # Logique buy1 → buy2 → buy3
    if signal.startswith("buy"):
        allowed = {
            "buy1": "none",
            "buy2": "buy1",
            "buy3": "buy2"
        }
        expected_previous = allowed.get(signal)

        if expected_previous is None or current_status != expected_previous:
            return jsonify({"status": f"Ignored: invalid order sequence ({signal})"}), 200

        # Calculer le solde et volume à 30%
        cad_balance = get_available_balance("ZCAD")
        allocation = cad_balance * 0.3

        # Obtenir prix actuel pour conversion (via Ticker)
        try:
            ticker = api.query_public("Ticker", {"pair": symbol})
            ask_price = float(ticker["result"][list(ticker["result"].keys())[0]]["a"][0])
            volume_to_buy = round(allocation / ask_price, 6)
        except Exception as e:
            return jsonify({"error": f"Erreur récupération prix : {str(e)}"}), 500

        response = place_market_order(symbol, volume_to_buy)
        position_status[account][symbol]["status"] = signal
        return jsonify({"status": f"{signal} executed", "kraken_response": response}), 200

    elif signal == "close":
        if current_status == "none":
            return jsonify({"status": "No position to close"}), 200
        # Ici on ne vend pas encore (à implémenter si souhaité)
        position_status[account][symbol]["status"] = "none"
        return jsonify({"status": "Position reset on close"}), 200

    return jsonify({"status": "Unhandled signal"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
