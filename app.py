#!/usr/bin/env python3
# app.py - EAGLEX CASINO complete backend with robust error handling
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import random, time, uuid, os, json, traceback, sys

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

DB_FILE = "casino_store.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "users": {
            "demo_user": {
                "id": "demo_user",
                "demo_balance": 5000.0,
                "real_balance": 0.0,
                "currency": "KES",
                "transactions": []
            }
        },
        "settings": {
            "paybill": "880100",
            "account_number": "1004508555",
            "min_deposit": 50,
            "min_play": 20,
            "min_withdraw": 500
        }
    }

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

DB = load_db()
USER = DB["users"]["demo_user"]

SYMBOLS = [
    "🍒","🍋","🍊","🍉","🍇","🍓","🥭","🍍","🍑","🍈",
    "7️⃣","🔔","⭐","💎","💰","🎲","🎰",
    "🚗","🏎️","🚀","🛩️","🚁","🚤",
    "🍔","🍕","🍟","🍩","🍪","🍫","🍦","🍰",
    "👑","🧧","🎁","🪙","📿","🔮",
    "🐶","🐱","🦁","🐯","🦄","🐉",
    "♠️","♥️","♦️","♣️","🃏","🎟️"
]

PAYOUT_RULES = {
    "7️⃣": 100,
    "💎": 50,
    "💰": 30,
    "⭐": 20,
    "🔔": 15,
    "🍒": 10,
    "default": 2
}

def record_transaction(user, t_type, amount, note=""):
    tx = {
        "id": str(uuid.uuid4()),
        "type": t_type,
        "amount": amount,
        "demo_balance": user.get("demo_balance", 5000.0),
        "real_balance": user.get("real_balance", 0.0),
        "note": note,
        "timestamp": int(time.time())
    }
    user["transactions"].append(tx)
    save_db(DB)
    return tx

@app.errorhandler(Exception)
def handle_uncaught_exception(e):
    tb = traceback.format_exc()
    print("UNCAUGHT EXCEPTION:", file=sys.stderr)
    print(tb, file=sys.stderr)
    return jsonify({"error": "Internal server error", "detail": str(e)}), 500

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/deposit")
def deposit_page():
    s = DB.get("settings", {})
    instructions = {
        "title": "Deposit Instructions",
        "currency": "KES",
        "minimum_deposit": s.get("min_deposit", 50),
        "paybill": f"PAYBILL {s.get('paybill','880100')}",
        "account_number": f"ACCOUNT {s.get('account_number','1004508555')}",
        "instructions": [
            "Open your mobile money app (M-Pesa or your provider).",
            f"Select Paybill and enter the Paybill number: PAYBILL {s.get('paybill','880100')}.",
            f"For Account Number enter: ACCOUNT {s.get('account_number','1004508555')}.",
            f"Enter the amount (minimum {s.get('min_deposit',50)} KES).",
            "Confirm and send. Keep the transaction receipt.",
            "After sending, go to Support and submit your receipt for manual crediting (demo)."
        ],
        "note": "This page shows instructions only. Replace placeholders with real payment integration in production."
    }
    return jsonify(instructions)

@app.route("/api/balance")
def api_balance():
    settings = DB.get("settings", {})
    return jsonify({
        "demo_balance": USER.get("demo_balance", 5000.0),
        "real_balance": USER.get("real_balance", 0.0),
        "currency": USER.get("currency", "KES"),
        "min_deposit": settings.get("min_deposit", 50),
        "min_play": settings.get("min_play", 20),
        "min_withdraw": settings.get("min_withdraw", 500)
    })

@app.route("/api/transactions")
def api_transactions():
    return jsonify({"transactions": USER["transactions"][-200:]})

@app.route("/api/spin", methods=["POST"])
def api_spin():
    try:
        data = request.get_json(force=True)
        bet = float(data.get("bet", 0))
        mode = str(data.get("mode", "real")).lower()
        settings = DB.get("settings", {})
        min_play = settings.get("min_play", 20)

        if bet <= 0:
            return jsonify({"error": "Invalid bet amount"}), 400
        if bet < min_play:
            return jsonify({"error": f"Minimum play amount is KES {min_play}"}), 400

        balance_key = "demo_balance" if mode == "demo" else "real_balance"
        if USER.get(balance_key, 0.0) < bet:
            if mode == "real":
                return jsonify({"error": "Insufficient real balance. Please deposit to play in Real mode."}), 402
            else:
                return jsonify({"error": "Insufficient demo balance."}), 400

        USER[balance_key] -= bet
        record_transaction(USER, "bet", -bet, note=f"Spin bet ({mode})")

        if mode == "demo":
            win_chance = 0.78
            big_win_chance = 0.18
            multiplier_boost = 1.9
        else:
            win_chance = 0.30
            big_win_chance = 0.02
            multiplier_boost = 1.0

        is_win = random.random() < win_chance

        visible = []
        for _ in range(3):
            reel = [random.choice(SYMBOLS) for _ in range(20)]
            visible.append([random.choice(reel) for _ in range(3)])

        center = [v[1] for v in visible]
        payout = 0.0
        win_symbols = []

        if is_win:
            if mode == "demo" and random.random() < big_win_chance:
                preferred = ["7️⃣", "💎", "💰"]
                sym = random.choice(preferred)
            else:
                keys = [k for k in PAYOUT_RULES.keys() if k != "default"]
                sym = random.choice(keys + SYMBOLS)
                if sym == "default":
                    sym = random.choice(SYMBOLS)

            for i in range(3):
                visible[i][1] = sym
            center = [visible[i][1] for i in range(3)]

            base_multiplier = PAYOUT_RULES.get(sym, PAYOUT_RULES["default"])
            multiplier = base_multiplier * multiplier_boost

            if mode == "demo" and random.random() < big_win_chance:
                multiplier *= random.choice([2, 3])

            payout = bet * multiplier
            USER[balance_key] += payout
            record_transaction(USER, "win", payout, note=f"Matched {sym} x3 ({mode})")
            win_symbols = center
        else:
            if mode == "demo" and random.random() < 0.08:
                sym = random.choice(SYMBOLS)
                visible[0][1] = sym
                visible[1][1] = sym
                visible[2][1] = random.choice([s for s in SYMBOLS if s != sym])
                center = [v[1] for v in visible]
                payout = bet * 1.2
                USER[balance_key] += payout
                record_transaction(USER, "win", payout, note=f"Demo consolation two-match")
                win_symbols = center
            else:
                win_symbols = center

        save_db(DB)
        return jsonify({
            "reels": visible,
            "center": center,
            "payout": payout,
            "demo_balance": USER.get("demo_balance", 5000.0),
            "real_balance": USER.get("real_balance", 0.0),
            "balance_used": balance_key,
            "win_symbols": win_symbols,
            "mode": mode,
            "timestamp": int(time.time())
        })
    except Exception as e:
        tb = traceback.format_exc()
        print("Exception in /api/spin:", file=sys.stderr)
        print(tb, file=sys.stderr)
        return jsonify({"error": "Internal server error during spin", "detail": str(e)}), 500

@app.route("/api/credit_demo", methods=["POST"])
def api_credit_demo():
    try:
        data = request.get_json(force=True)
        amount = float(data.get("amount", 0))
        if amount <= 0:
            return jsonify({"error": "Invalid amount"}), 400
        USER["demo_balance"] += amount
        tx = record_transaction(USER, "deposit_demo", amount, note="Manual demo credit")
        return jsonify({"status": "ok", "transaction": tx, "demo_balance": USER["demo_balance"]})
    except Exception as e:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500

@app.route("/api/credit_real", methods=["POST"])
def api_credit_real():
    try:
        data = request.get_json(force=True)
        amount = float(data.get("amount", 0))
        if amount < DB.get("settings", {}).get("min_deposit", 50):
            return jsonify({"error": f"Minimum deposit is KES {DB.get('settings',{}).get('min_deposit',50)}"}), 400
        USER["real_balance"] += amount
        tx = record_transaction(USER, "deposit_real", amount, note="Manual real credit (after deposit)")
        return jsonify({"status": "ok", "transaction": tx, "real_balance": USER["real_balance"]})
    except Exception as e:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500

@app.route("/api/withdraw_methods")
def api_withdraw_methods():
    methods = [
        {"id":"bank","label":"Bank Transfer"},
        {"id":"mpesa","label":"M-Pesa Transfer"},
        {"id":"paypal","label":"PayPal"},
        {"id":"crypto","label":"Crypto (BTC/ETH)"},
        {"id":"airtel","label":"Airtel Money"},
        {"id":"cashpickup","label":"Cash Pickup"}
    ]
    return jsonify({"min_withdraw": DB.get("settings",{}).get("min_withdraw",500), "methods": methods})

@app.route("/api/withdraw", methods=["POST"])
def api_withdraw():
    try:
        data = request.get_json(force=True)
        amount = float(data.get("amount", 0))
        method = data.get("method", "")
        details = data.get("details", "")
        min_w = DB.get("settings",{}).get("min_withdraw",500)
        if amount < min_w:
            return jsonify({"error": f"Minimum withdrawal is KES {min_w}"}), 400
        if amount > USER.get("real_balance", 0.0):
            return jsonify({"error": "Insufficient real balance"}), 400
        USER["real_balance"] -= amount
        tx = record_transaction(USER, "withdraw_request", -amount, note=f"Withdraw via {method}")
        save_db(DB)
        return jsonify({"status":"pending","transaction":tx,"message":"Withdrawal request received. Admin will process manually in demo."})
    except Exception as e:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500

if __name__ == "__main__":
    save_db(DB)
    app.run(host="0.0.0.0", port=5000, debug=True)

