print("🚀 main.py bien déployé avec prepare_buy")

from flask import Flask, request, jsonify
import os
import krakenex
from dotenv import load_dotenv
from google_sheets_logger import update_status, log_trade

app = Flask(__name__)
load_dotenv()

api = krakenex.API()
api.key = os.getenv("KRAKEN_API_KEY")
api.secret = os.getenv("KRAKEN_API_SECRET")

position_steps = {}

@app.route("/", methods=["GET"])
def home():
    return "Kraken Bot is live!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400

    strategy = data.get("strategy")
    signal = data.get("signal")
    symbol = data.get("symbol")
    account = data.get("account")

    if strategy != "Env24":
        return jsonify({"status": "Ignored: Not Env24 strategy"}), 200

    key = f"{account}_{symbol}"
    step = position_steps.get(key, 0)

    if signal == "prepare_buy":
        return handle_prepare_buy(account)

    if signal == "buy1" and step == 0:
        return handle_buy(account, symbol, 1, key)
    elif signal == "buy2" and step == 1:
        return handle_buy(account, symbol, 2, key)
    elif signal == "buy3" and step == 2:
        return handle_buy(account, symbol, 3, key)
    elif signal == "close" and step > 0:
        return handle_close(account, symbol, key)
    else:
        return jsonify({"status": f"Ignored: invalid order sequence ({signal})"}), 200

def handle_prepare_buy(account):
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

def handle_buy(account, symbol, step, key):
    try:
        balance = api.query_private("Balance")
        volume_to_use = float(balance["result"].get("ZUSD", 0.0)) * 0.3
        if volume_to_use <= 5:
            return jsonify({"status": "Not enough USD balance for buy"}), 200

        price_info = api.query_public("Ticker", {"pair": symbol.replace("/", "")})
        price = float(list(price_info["result"].values())[0]["c"][0])
        volume = round(volume_to_use / price, 8)

        response = api.query_private("AddOrder", {
            "pair": symbol.replace("/", ""),
            "type": "buy",
            "ordertype": "market",
            "volume": str(volume)
        })
        txid = response.get("result", {}).get("txid", ["?"])[0]
        position_steps[key] = step
        log_trade(account, symbol, f"buy{step}", volume, "buy", txid, price)
        update_status(account, symbol, step, f"buy{step}", txid)
        return jsonify({"status": f"buy{step} executed", "kraken_response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e), "status": f"buy{step} failed"}), 500

def handle_close(account, symbol, key):
    try:
        balance = api.query_private("Balance")
        crypto_code = "X" + symbol.split("/")[0]
        volume = balance["result"].get(crypto_code, "0")
        if float(volume) == 0:
            return jsonify({"status": "Nothing to sell", "volume": volume}), 200

        response = api.query_private("AddOrder", {
            "pair": symbol.replace("/", ""),
            "type": "sell",
            "ordertype": "market",
            "volume": volume
        })
        txid = response.get("result", {}).get("txid", ["?"])[0]
        log_trade(account, symbol, "close", volume, "sell", txid)
        update_status(account, symbol, 0, "close", txid)
        position_steps[key] = 0
        return jsonify({"status": "Position closed", "kraken_response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e), "status": "close failed"}), 500

@app.route("/debug/balance", methods=["GET"])
def debug_balance():
    try:
        balance = api.query_private("Balance")
        return jsonify(balance)
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
