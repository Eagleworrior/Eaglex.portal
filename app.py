#!/usr/bin/env python3
# EAGLEX CASINO - full app with auth, demo/real, neon API

from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_cors import CORS
import random, time, uuid, os, json, traceback, sys

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "CHANGE_THIS_SECRET_KEY_FOR_PRODUCTION"
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
        "users": {},
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
settings = DB.setdefault("settings", {})
settings.setdefault("paybill", "880100")
settings.setdefault("account_number", "1004508555")
settings.setdefault("min_deposit", 50)
settings.setdefault("min_play", 20)
settings.setdefault("min_withdraw", 500)
save_db(DB)

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

def get_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return DB["users"].get(uid)

def ensure_user_defaults(user):
    user.setdefault("demo_balance", 5000.0)
    user.setdefault("real_balance", 0.0)
    user.setdefault("currency", "KES")
    user.setdefault("transactions", [])

def record_transaction(user, t_type, amount, note=""):
    ensure_user_defaults(user)
    tx = {
        "id": str(uuid.uuid4()),
        "type": t_type,
        "amount": amount,
        "demo_balance": user.get("demo_balance", 0.0),
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

# ---------- AUTH ROUTES ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            return render_template("register.html", error="All fields are required.")
        if username in DB["users"]:
            return render_template("register.html", error="Username already exists.")
        DB["users"][username] = {
            "id": username,
            "username": username,
            "password": password,  # demo only
            "demo_balance": 5000.0,
            "real_balance": 0.0,
            "currency": "KES",
            "transactions": []
        }
        save_db(DB)
        session["user_id"] = username
        return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = DB["users"].get(username)
        if not user or user.get("password") != password:
            return render_template("login.html", error="Invalid username or password.")
        session["user_id"] = username
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))

# ---------- PAGES ----------

@app.route("/")
def index():
    user = get_user()
    if not user:
        return redirect(url_for("login"))
    ensure_user_defaults(user)
    return render_template("index.html", username=user["username"])

@app.route("/deposit")
def deposit_page():
    user = get_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    s = DB.get("settings", {})
    instructions = {
        "title": "Brilliant Neon Deposit Guide",
        "currency": "KES",
        "minimum_deposit": s.get("min_deposit", 50),
        "paybill": f"PAYBILL {s.get('paybill','880100')}",
        "account_number": f"ACCOUNT {s.get('account_number','1004508555')}",
        "instructions": [
            "Launch your mobile money app in full glory (M-Pesa or your provider).",
            f"Tap Paybill and enter the glowing Paybill number: {s.get('paybill','880100')}.",
            f"In Account Number, type this magic code: {s.get('account_number','1004508555')}.",
            f"Enter your amount (minimum {s.get('min_deposit',50)} KES) and confirm.",
            "Wait for the confirmation SMS and keep that receipt safe.",
            "Return here and contact Support to have your REAL balance credited (demo mode)."
        ],
        "note": "This is a demo instruction page. Integrate real payment APIs before going live."
    }
    return jsonify(instructions)

# ---------- API ----------

@app.route("/api/balance")
def api_balance():
    user = get_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    ensure_user_defaults(user)
    s = DB.get("settings", {})
    return jsonify({
        "username": user["username"],
        "demo_balance": user.get("demo_balance", 0.0),
        "real_balance": user.get("real_balance", 0.0),
        "currency": user.get("currency", "KES"),
        "min_deposit": s.get("min_deposit", 50),
        "min_play": s.get("min_play", 20),
        "min_withdraw": s.get("min_withdraw", 500)
    })

@app.route("/api/transactions")
def api_transactions():
    user = get_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    ensure_user_defaults(user)
    return jsonify({"transactions": user["transactions"][-200:]})

@app.route("/api/spin", methods=["POST"])
def api_spin():
    user = get_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    ensure_user_defaults(user)
    try:
        data = request.get_json(force=True)
        bet = float(data.get("bet", 0))
        mode = str(data.get("mode", "real")).lower()
        s = DB.get("settings", {})
        min_play = s.get("min_play", 20)

        if bet <= 0:
            return jsonify({"error": "Invalid bet amount"}), 400
        if bet < min_play:
            return jsonify({"error": f"Minimum play amount is KES {min_play}"}), 400

        balance_key = "demo_balance" if mode == "demo" else "real_balance"
        if user.get(balance_key, 0.0) < bet:
            if mode == "real":
                return jsonify({"error": "Insufficient real balance. Please deposit to play in REAL mode."}), 402
            else:
                return jsonify({"error": "Insufficient demo balance."}), 400

        user[balance_key] -= bet
        record_transaction(user, "bet", -bet, note=f"Spin bet ({mode})")

        if mode == "demo":
            win_chance = 0.80
            big_win_chance = 0.20
            multiplier_boost = 2.0
        else:
            win_chance = 0.20
            big_win_chance = 0.03
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
            user[balance_key] += payout
            record_transaction(user, "win", payout, note=f"Matched {sym} x3 ({mode})")
            win_symbols = center
        else:
            if mode == "demo" and random.random() < 0.10:
                sym = random.choice(SYMBOLS)
                visible[0][1] = sym
                visible[1][1] = sym
                visible[2][1] = random.choice([s for s in SYMBOLS if s != sym])
                center = [v[1] for v in visible]
                payout = bet * 1.2
                user[balance_key] += payout
                record_transaction(user, "win", payout, note="Demo consolation two-match")
                win_symbols = center
            else:
                win_symbols = center

        save_db(DB)
        return jsonify({
            "reels": visible,
            "center": center,
            "payout": payout,
            "demo_balance": user.get("demo_balance", 0.0),
            "real_balance": user.get("real_balance", 0.0),
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

@app.route("/api/withdraw_methods")
def api_withdraw_methods():
    user = get_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
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
    user = get_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    ensure_user_defaults(user)
    try:
        data = request.get_json(force=True)
        amount = float(data.get("amount", 0))
        method = data.get("method", "")
        details = data.get("details", "")
        min_w = DB.get("settings",{}).get("min_withdraw",500)
        if amount < min_w:
            return jsonify({"error": f"Minimum withdrawal is KES {min_w}"}), 400
        if amount > user.get("real_balance", 0.0):
            return jsonify({"error": "Insufficient real balance"}), 400
        user["real_balance"] -= amount
        tx = record_transaction(user, "withdraw_request", -amount, note=f"Withdraw via {method} ({details})")
        save_db(DB)
        return jsonify({"status":"pending","transaction":tx,"message":"Withdrawal request received. Admin will process manually in demo."})
    except Exception as e:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500

if __name__ == "__main__":
    save_db(DB)
    app.run(host="0.0.0.0", port=5000, debug=True)

