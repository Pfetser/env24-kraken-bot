
from flask import Flask, request, jsonify
import os
import krakenex
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

api = krakenex.API()
api.key = os.getenv("KRAKEN_API_KEY")
api.secret = os.getenv("KRAKEN_API_SECRET")

@app.route("/", methods=["GET"])
def home():
    return "Bot Env24 - Affichage complet du solde 🔍"

@app.route("/debug/balance", methods=["GET"])
def debug_balance():
    try:
        response = api.query_private("Balance")
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
