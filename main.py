from flask import Flask, request, jsonify
import os
import krakenex
import requests
from datetime import datetime
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

api = krakenex.API()
api.key = os.getenv("KRAKEN_API_KEY")
api.secret = os.getenv("KRAKEN_API_SECRET")

SUPABASE_URL = "https://bbsttyqzcikgkneaybdq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJic3R0eXF6Y2lrZ2tuZWF5YmRxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQyMTc5MTQsImV4cCI6MjA1OTc5MzkxNH0.pRFopBJ-KrX7cEwSrN-39HJUnSu-y5OEbAQDo4VvEuc"

position_status = {}

def log_trade(data):
    url = f"{SUPABASE_URL}/rest/v1/trades"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    r = requests.post(url, json=data, headers=headers)
    return r.json()

def get_available_balance(currency="ZCAD"):
    try:
        balance = api.query_private("Balance")
        return float(balance["result"].get(currency, 0))
    except Exception:
        return 0

def get_price(pair):
    try:
        ticker = api.query_public("Ticker", {"pair": pair})
        return float(ticker["result"][list(ticker["result"].keys())[0]]["a"][0])
    except:
        return None

def place_market_order(pair, volume, side="buy"):
    try:
        response = api.query_private("AddOrder", {
            "pair": pair,
            "type": side,
            "ordertype": "market",
            "volume": str(volume)
        })
        return response
    except Exception as e:
        return {"error": str(e)}

@app.route("/", methods=["GET"])
def home():
    return "Bot Env24 avec log Supabase ✅"

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

        if signal == "buy1" or "initial_cad" not in symbol_status:
            initial_cad = get_available_balance("ZCAD")
            symbol_status["initial_cad"] = initial_cad

        allocation = symbol_status["initial_cad"] * 0.3
        price = get_price(symbol)
        if not price:
            return jsonify({"error": "Could not retrieve price"}), 500

        volume = round(allocation / price, 6)
        volume = max(volume, 0.0001)
        response = place_market_order(symbol, volume, side="buy")

        if "error" in response and response["error"]:
            return jsonify({"status": "Kraken error", "kraken_response": response}), 400

        txid = response["result"]["txid"][0]
        amount_cad = round(volume * price, 2)

        log_trade({
            "created_at": datetime.utcnow().isoformat(),
            "account": account,
            "symbol": symbol,
            "signal": signal,
            "volume": volume,
            "price": price,
            "amount_cad": amount_cad,
            "txid": txid
        })

        symbol_status["status"] = signal
        return jsonify({"status": f"{signal} executed", "kraken_response": response}), 200

    elif signal == "close":
        if current_status == "none":
            return jsonify({"status": "No position to close"}), 200

        base = symbol[:3]
        kraken_base_key = {
            "BTC": "XXBT", "ETH": "XETH", "SOL": "XSOL", "ADA": "XADA", "XRP": "XXRP"
        }.get(base, "X" + base)

        volume = get_available_balance(kraken_base_key)
        if volume < 0.0001:
            return jsonify({"status": "Nothing to sell", "volume": volume}), 200

        price = get_price(symbol)
        response = place_market_order(symbol, volume, side="sell")

        if "error" in response and response["error"]:
            return jsonify({"status": "Kraken error", "kraken_response": response}), 400

        txid = response["result"]["txid"][0]
        amount_cad = round(volume * price, 2)

        log_trade({
            "created_at": datetime.utcnow().isoformat(),
            "account": account,
            "symbol": symbol,
            "signal": "close",
            "volume": volume,
            "price": price,
            "amount_cad": amount_cad,
            "txid": txid
        })

        symbol_status["status"] = "none"
        symbol_status.pop("initial_cad", None)

        return jsonify({"status": "Position closed and sold", "kraken_response": response}), 200

    return jsonify({"status": "Unhandled signal"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

