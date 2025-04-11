import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

# Configuration d'accès à l'API Google Sheets
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Utilise la variable d'environnement pour les credentials (JSON au format string)
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
CREDS = Credentials.from_service_account_info(eval(GOOGLE_CREDENTIALS_JSON), scopes=SCOPE)

gs_client = gspread.authorize(CREDS)
SPREADSHEET_ID = "1uyG-QNpWrb0FxV1r09Lc2L-3e1hzQ9eLM9ONQbcEg1Q"
sheet = gs_client.open_by_key(SPREADSHEET_ID)

# Mise à jour de l'état en temps réel
def update_status(account, symbol, step, signal, txid=""):
    try:
        ws = sheet.worksheet("Suivi en temps réel")
        rows = ws.get_all_records()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Rechercher la ligne à mettre à jour
        for i, row in enumerate(rows):
            if row["Compte"] == account and row["Crypto active"] == symbol:
                ws.update(f"A{i+2}:H{i+2}", [[
                    now, account, symbol, step,
                    "Oui" if step == 0 else "Non",
                    signal, txid, "Auto"
                ]])
                return

        # Si aucune ligne trouvée, ajouter une nouvelle entrée
        ws.append_row([
            now, account, symbol, step,
            "Oui" if step == 0 else "Non",
            signal, txid, "Auto"
        ])
    except Exception as e:
        print("Erreur update_status:", e)

# Journalisation d'un trade
def log_trade(account, symbol, signal, volume, trade_type, txid="", price="?"):
    try:
        ws = sheet.worksheet("Journal de trading")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ws.append_row([
            now, account, symbol, signal,
            volume, price, trade_type, "", txid
        ])
    except Exception as e:
        print("Erreur log_trade:", e)
