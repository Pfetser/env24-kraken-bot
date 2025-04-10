from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import krakenex
from google_sheets_logger import log_trade, update_status

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

@app.route("/staking-assets", methods=["GET"])
def staking_assets():
    response = api.query_private("Staking/Assets")
    return jsonify(response)

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
        update_status(account, symbol, 0, "reset")
        return jsonify({"status": f"Position reset for {symbol}"}), 200

    if signal == "prepare_buy":
        try:
            balance = api.query_private("Balance")
            staking_targets = ["ADA", "MINA", "TAO"]
            for crypto in staking_targets:
                if f"X{crypto}" in balance["result"]:
                    volume = balance["result"][f"X{crypto}"]
                    response = api.query_private("AddOrder", {
                        "pair": f"{crypto}USD",
                        "type": "sell",
                        "ordertype": "market",
                        "volume": volume
                    })
                    txid = response.get("result", {}).get("txid", ["?"])[0]
                    log_trade(account, f"{crypto}/USD", "prepare_sell", volume, "sell", txid)
                    update_status(account, f"{crypto}/USD", 0, "prepare_sell", txid)
                    return jsonify({"status": f"Staking sold for {crypto}", "txid": txid}), 200
            return jsonify({"status": "No staked asset found to sell"}), 200
        except Exception as e:
            return jsonify({"error": str(e), "status": "prepare_buy failed"}), 500

    if signal == "buy1":
        if state["step"] >= 1:
            return jsonify({"status": "Ignored: invalid order sequence (buy1)"}), 200
        response = api.query_private("AddOrder", {
            "pair": symbol.replace("/", ""),
            "type": "buy",
            "ordertype": "market",
            "volume": "0.0001"
        })
        txid = response.get("result", {}).get("txid", ["?"])[0]
        log_trade(account, symbol, "buy1", "0.0001", "buy", txid)
        update_status(account, symbol, 1, "buy1", txid)
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
        txid = response.get("result", {}).get("txid", ["?"])[0]
        log_trade(account, symbol, "buy2", "0.0001", "buy", txid)
        update_status(account, symbol, 2, "buy2", txid)
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
        txid = response.get("result", {}).get("txid", ["?"])[0]
        log_trade(account, symbol, "buy3", "0.0001", "buy", txid)
        update_status(account, symbol, 3, "buy3", txid)
        position_state[key] = {"step": 3}
        return jsonify({"status": "buy3 executed", "kraken_response": response}), 200

    if signal == "close":
        response = api.query_private("AddOrder", {
            "pair": symbol.replace("/", ""),
            "type": "sell",
            "ordertype": "market",
            "volume": "0.0006"
        })
        txid = response.get("result", {}).get("txid", ["?"])[0]
        log_trade(account, symbol, "close", "0.0006", "sell", txid)
        update_status(account, symbol, 0, "close", txid)
        position_state[key] = {"step": 0}
        return jsonify({"status": "Position closed", "kraken_response": response}), 200

    return jsonify({"status": "Signal not handled"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
