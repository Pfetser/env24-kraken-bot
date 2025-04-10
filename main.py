from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import krakenex

app = Flask(__name__)
load_dotenv()

api = krakenex.API()
api.key = os.getenv("KRAKEN_API_KEY")
api.secret = os.getenv("KRAKEN_API_SECRET")

position_state = {}

@app.route("/", methods=["GET"])
def home():
    return "Bot Env24 avec log Supabase ✅"

@app.route("/status", methods=["GET"])
def status():
    return jsonify(position_state)

@app.route("/debug/staking-assets", methods=["GET"])
def debug_staking_assets():
    try:
        response = api.query_private("Staking/Assets")
        if response.get("error"):
            return jsonify({"status": "error", "kraken_error": response["error"]})
        return jsonify({"status": "success", "result": response.get("result")})
    except Exception as e:
        return jsonify({"status": "exception", "message": str(e)}), 500

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Webhook received:", data)

    strategy = data.get("strategy")
    platform = data.get("platform")
    account = data.get("account")
    symbol = data.get("symbol")
    signal = data.get("signal")

    if strategy != "Env24":
        return jsonify({"status": "Ignored: not Env24"}), 200

    key = f"{account}_{symbol}"
    state = position_state.get(key, {"step": 0})

    if signal == "reset":
        position_state[key] = {"step": 0}
        return jsonify({"status": f"Position reset for {symbol}"}), 200

    if signal == "buy1":
        if state["step"] >= 1:
            return jsonify({"status": "Ignored: invalid order sequence (buy1)"}), 200
        response = api.query_private("AddOrder", {
            "pair": symbol.replace("/", ""),
            "type": "buy",
            "ordertype": "market",
            "volume": "0.0001"
        })
        position_state[key] = {"step": 1}
        return jsonify({"status": "buy1 executed", "kraken_response": response}), 200

    if signal == "buy2":
        if state["step"] != 1:
            return jsonify({"status": "Ignored: invalid order sequence (buy2)"}), 200
        response = api.query_private("AddOrder", {
            "pair": symbol.replace("/", ""),
            "type": "buy",
            "ordertype": "market",
            "volume": "0.0001"
        })
        position_state[key] = {"step": 2}
        return jsonify({"status": "buy2 executed", "kraken_response": response}), 200

    if signal == "buy3":
        if state["step"] != 2:
            return jsonify({"status": "Ignored: invalid order sequence (buy3)"}), 200
        response = api.query_private("AddOrder", {
            "pair": symbol.replace("/", ""),
            "type": "buy",
            "ordertype": "market",
            "volume": "0.0001"
        })
        position_state[key] = {"step": 3}
        return jsonify({"status": "buy3 executed", "kraken_response": response}), 200

    if signal == "close":
        response = api.query_private("AddOrder", {
            "pair": symbol.replace("/", ""),
            "type": "sell",
            "ordertype": "market",
            "volume": "0.0006"
        })
        position_state[key] = {"step": 0}
        return jsonify({"status": "Position closed", "kraken_response": response}), 200

    return jsonify({"status": "Signal not handled"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
