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
staking_status = {}

staking_supported = {
    "ADA": {"delay": 0},
    "MINA": {"delay": 0},
    "TAO": {"delay": 0},
    "KAVA": {"delay": 0},
    "FLOW": {"delay": 0},
    "OSMO": {"delay": 0}
}

@app.route("/", methods=["GET"])
def home():
    return "Bot Env24 avec staking intelligent (CAD+USD) ✅"

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"position_state": position_state, "staking_status": staking_status})

@app.route("/debug/staking", methods=["GET"])
def debug_staking():
    return jsonify({"staking_status": staking_status})

@app.route("/force-stake", methods=["GET"])
def force_stake():
    symbol = request.args.get("symbol")
    account = request.args.get("account")
    if not symbol or not account:
        return jsonify({"error": "Missing symbol or account"}), 400

    asset = symbol.split("/")[0].upper()
    key = f"{account}_{symbol}"

    if asset in staking_supported:
        try:
            response = api.query_private("Stake", {"asset": asset, "method": "staking"})
            staking_status[key] = True
            return jsonify({"status": "Staking command sent", "asset": asset, "response": response}), 200
        except Exception as e:
            return jsonify({"status": "Staking failed", "error": str(e)}), 500
    else:
        return jsonify({"status": f"Asset {asset} not eligible for staking"}), 400

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
    asset = symbol.split("/")[0].upper()
    state = position_state.get(key, {"step": 0})

    if state["step"] == 0 and asset in staking_supported and not staking_status.get(key):
        stake_resp = api.query_private("Stake", {"asset": asset, "method": "staking"})
        staking_status[key] = True
        print(f"Staked {asset}")

    if signal == "prepare_buy1":
        if asset in staking_supported and staking_status.get(key):
            unstake_resp = api.query_private("Unstake", {"asset": asset})
            staking_status[key] = False
            return jsonify({"status": "Unstaked in preparation for buy", "response": unstake_resp}), 200
        return jsonify({"status": "No staking active or unsupported asset"}), 200

    if signal == "reset":
        position_state[key] = {"step": 0}
        staking_status[key] = False
        return jsonify({"status": f"Position reset for {symbol}"}), 200

    if signal == "buy1":
        if state["step"] >= 1:
            return jsonify({"status": "Ignored: invalid order sequence (buy1)"}), 200
        if staking_status.get(key):
            unstake_resp = api.query_private("Unstake", {"asset": asset})
            staking_status[key] = False
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
        staking_status[key] = False
        return jsonify({"status": "Position closed", "kraken_response": response}), 200

    return jsonify({"status": "Signal not handled"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

