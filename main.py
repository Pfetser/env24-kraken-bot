
from flask import Flask, request, jsonify
import os
import krakenex
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

api = krakenex.API()
api.key = os.getenv("KRAKEN_API_KEY")
api.secret = os.getenv("KRAKEN_API_SECRET")

position_open = False

@app.route("/", methods=["GET"])
def home():
    return "Env24 Kraken bot is live 🚀"

@app.route("/webhook", methods=["POST"])
def webhook():
    global position_open
    data = request.json

    if not data:
        return jsonify({"error": "No data received"}), 400

    strategy = data.get("strategy")
    signal = data.get("signal")
    symbol = data.get("symbol", "BTC/CAD")

    if strategy != "Env24":
        return jsonify({"status": "Ignored: Not Env24 strategy"}), 200

    if signal.startswith("buy"):
        if position_open:
            return jsonify({"status": "Position already open, no action taken"}), 200
        try:
            response = api.query_private("AddOrder", {
                "pair": "XBTCAD",
                "type": "buy",
                "ordertype": "market",
                "volume": "0.0001"
            })
            position_open = True
            return jsonify({"status": "Order sent", "kraken_response": response}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif signal == "close":
        position_open = False
        return jsonify({"status": "Position closed manually"}), 200

    return jsonify({"status": "No matching action"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
