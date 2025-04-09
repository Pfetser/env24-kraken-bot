
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
    return "Bot Env24 avec allocation fixe 🚀"

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

    if account not in position_status:
        position_status[account] = {}
    if symbol not in position_status[account]:
        position_status[account][symbol] = {"status": "none"}

    current_status = position_status[account][symbol]["status"]
    symbol_status = position_status[account][symbol]

    allowed = {
        "buy1": "none",
        "buy2": "buy1",
        "buy3": "buy2"
    }

    if signal.startswith("buy"):
        expected_previous = allowed.get(signal)
        if expected_previous is None or current_status != expected_previous:
            return jsonify({"status": f"Ignored: invalid order sequence ({signal})"}), 200

        # Au buy1, enregistrer le solde initial
        if signal == "buy1" or "initial_cad" not in symbol_status:
            initial_cad = get_available_balance("ZCAD")
            symbol_status["initial_cad"] = initial_cad

        initial_cad = symbol_status.get("initial_cad", 0)
        allocation = initial_cad * 0.3

        try:
            ticker = api.query_public("Ticker", {"pair": symbol})
            ask_price = float(ticker["result"][list(ticker["result"].keys())[0]]["a"][0])
            volume_to_buy = round(allocation / ask_price, 6)
            volume_to_buy = max(volume_to_buy, 0.0001)
        except Exception as e:
            return jsonify({"error": f"Erreur récupération prix : {str(e)}"}), 500

        response = place_market_order(symbol, volume_to_buy)

        if "error" in response and response["error"]:
            return jsonify({"status": "Kraken error", "kraken_response": response}), 400

        symbol_status["status"] = signal
        return jsonify({"status": f"{signal} executed", "kraken_response": response}), 200

    elif signal == "close":
        if current_status == "none":
            return jsonify({"status": "No position to close"}), 200
        symbol_status["status"] = "none"
        symbol_status.pop("initial_cad", None)
        return jsonify({"status": "Position reset on close"}), 200

    return jsonify({"status": "Unhandled signal"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
