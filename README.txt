
=== Env24 Kraken Bot - Installation Guide ===

1. Crée un nouveau dépôt GitHub (ex: env24-kraken-bot)
2. Clone le dépôt sur ton Mac :
   git clone https://github.com/TON_UTILISATEUR/env24-kraken-bot.git
3. Remplace les fichiers par ceux de ce dossier :
   - main.py
   - requirements.txt

4. Push sur GitHub :
   git add .
   git commit -m "Initial commit - Env24 Kraken bot"
   git push origin main

5. Va sur https://dashboard.render.com et crée un nouveau service web :
   - Connecte ton nouveau repo GitHub
   - Start command = python main.py
   - Environment = production
   - Ajoute tes clés : KRAKEN_API_KEY / KRAKEN_API_SECRET

6. Test avec :
   curl -X POST https://TON_RENDER.onrender.com/webhook \
     -H "Content-Type: application/json" \
     -d '{"strategy":"Env24", "platform":"Kraken", "account":"Florent", "symbol":"BTC/USD", "signal":"buy1"}'
