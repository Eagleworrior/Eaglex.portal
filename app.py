#!/usr/bin/env python3
"""
Text-First Super-App (single-file, Kali-ready)
- Paste this file as ~/text_super_app/app.py
- Activate venv and run: uvicorn app:app --reload --host 127.0.0.1 --port 8000
- This file is self-contained and avoids accidental shell text or browser metadata.
"""

import os
import re
import json
import time
import ast
import math
import sqlite3
import subprocess
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, HTTPException
from pydantic import BaseModel
from rich.console import Console

# Optional features
try:
    from playsound import playsound
    _HAS_PLAYSOUND = True
except Exception:
    _HAS_PLAYSOUND = False

try:
    import pytesseract
    from PIL import Image
    _HAS_OCR = True
except Exception:
    _HAS_OCR = False

# App and console
app = FastAPI(title="Text-First Super-App (Kali Edition)")
console = Console()

# ---------------------------
# Simple persistence (SQLite)
# ---------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "superapp.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        last_active TEXT,
        context TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        module TEXT,
        command TEXT,
        result TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        amount REAL,
        currency TEXT,
        category TEXT,
        note TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

def log_event(module, command, result):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO logs (ts,module,command,result) VALUES (?,?,?,?)",
                (datetime.utcnow().isoformat(), module, command, json.dumps(result)))
    conn.commit()
    conn.close()

# ---------------------------
# Utilities: safe math eval
# ---------------------------
ALLOWED_AST_NODES = {
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
    ast.USub, ast.UAdd, ast.Call, ast.Name, ast.Tuple, ast.List,
    ast.Constant
}

SAFE_NAMES = {
    'abs': abs, 'round': round, 'min': min, 'max': max,
    'pow': pow, 'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
    'tan': math.tan, 'log': math.log, 'log10': math.log10
}

def safe_eval_expr(expr: str):
    """
    Safely evaluate arithmetic expressions and a small set of math functions.
    """
    try:
        node = ast.parse(expr, mode='eval')
    except Exception:
        raise ValueError("Invalid expression")
    for n in ast.walk(node):
        if not isinstance(n, tuple(ALLOWED_AST_NODES)):
            raise ValueError("Disallowed expression")
    code = compile(node, "<safe_eval>", "eval")
    return eval(code, {"__builtins__": {}}, SAFE_NAMES)

# ---------------------------
# Sanitized subprocess helper
# ---------------------------
def run_sanitized_command(cmd_list, timeout=30):
    """
    Run a subprocess with a sanitized command list.
    cmd_list must be a list of strings (no shell=True).
    """
    if not isinstance(cmd_list, (list, tuple)) or not cmd_list:
        raise ValueError("Invalid command")
    safe_re = re.compile(r'^[\w\-\./:]+$')
    for arg in cmd_list:
        if not safe_re.match(arg):
            raise ValueError("Unsafe argument detected")
    try:
        proc = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout)
        return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "timeout"}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}

# ---------------------------
# Module: Productivity
# ---------------------------
def productivity_handle(text: str, user: Optional[str] = None):
    t = text.lower()
    if "remind" in t or "reminder" in t:
        ts = datetime.utcnow().isoformat()
        result = {"status": "ok", "message": "Reminder saved", "text": text, "created_at": ts}
        log_event("Productivity", text, result)
        return result
    if "task" in t or "todo" in t:
        ts = datetime.utcnow().isoformat()
        result = {"status": "ok", "message": "Task added", "text": text, "created_at": ts}
        log_event("Productivity", text, result)
        return result
    return {"status": "unknown", "module": "Productivity", "text": text}

# ---------------------------
# Module: Security (Kali tools)
# ---------------------------
def security_handle(text: str):
    t = text.lower()
    if "scan" in t or "nmap" in t:
        m = re.search(r'(\d{1,3}(?:\.\d{1,3}){3}|localhost|127\.0\.0\.1|\w[\w\.-]+)', text)
        target = m.group(1) if m else "localhost"
        if not re.match(r'^(localhost|127\.0\.0\.1|\d{1,3}(?:\.\d{1,3}){3}|[a-zA-Z0-9\.-]+)$', target):
            return {"status": "error", "error": "Invalid target"}
        try:
            res = run_sanitized_command(["nmap", "-F", target], timeout=60)
        except ValueError as e:
            return {"status": "error", "error": str(e)}
        log_event("Security", text, res)
        return {"module": "Security", "action": "nmap", "target": target, "result": res}
    if "phishing" in t or "link" in t:
        result = {"module": "Security", "action": "phishing_check", "result": "placeholder: no suspicious links found"}
        log_event("Security", text, result)
        return result
    return {"status": "unknown", "module": "Security", "text": text}

# ---------------------------
# Module: Utilities (OCR, conversions, safe math, CSV export)
# ---------------------------
def utilities_handle(text: str, upload_file: Optional[UploadFile] = None):
    t = text.lower()
    if "ocr" in t or "read text" in t:
        if not _HAS_OCR:
            return {"status": "error", "error": "OCR not available; install pytesseract and tesseract-ocr"}
        try:
            if upload_file:
                tmp_path = os.path.join("/tmp", f"ocr_{int(time.time())}_{upload_file.filename}")
                with open(tmp_path, "wb") as f:
                    f.write(upload_file.file.read())
                img = Image.open(tmp_path)
            else:
                sample = os.path.join(os.path.dirname(__file__), "sample.png")
                if not os.path.exists(sample):
                    return {"status": "error", "error": "No image provided and sample.png missing"}
                img = Image.open(sample)
            text_out = pytesseract.image_to_string(img)
            result = {"module": "Utilities", "action": "ocr", "text": text_out}
            log_event("Utilities", text, result)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}
    if "calculate" in t or re.search(r'^\s*[\d\.\s\+\-\*\/\(\)]+$', text):
        expr = text
        if "calculate" in t:
            expr = text.split("calculate", 1)[1].strip()
        try:
            val = safe_eval_expr(expr)
            result = {"module": "Utilities", "action": "calculate", "expression": expr, "result": val}
            log_event("Utilities", text, result)
            return result
        except Exception as e:
            return {"status": "error", "error": "Calculation failed: " + str(e)}
    if "export" in t and "csv" in t:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT ts,module,command,result FROM logs ORDER BY id DESC LIMIT 100")
        rows = cur.fetchall()
        csv_path = os.path.join(os.path.dirname(__file__), "export_logs.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            import csv as _csv
            writer = _csv.writer(f)
            writer.writerow(["ts", "module", "command", "result"])
            for r in rows:
                writer.writerow(r)
        conn.close()
        return {"module": "Utilities", "action": "export_csv", "file": csv_path}
    if "convert" in t:
        return {"module": "Utilities", "action": "convert", "note": "conversion placeholder; integrate libreoffice or API"}
    return {"status": "unknown", "module": "Utilities", "text": text}

# ---------------------------
# Module: Entertainment (text games, trivia, audio)
# ---------------------------
def entertainment_handle(text: str, background: BackgroundTasks = None):
    t = text.lower()
    if "play" in t and "music" in t:
        if not _HAS_PLAYSOUND:
            return {"status": "error", "error": "Audio playback not available (playsound missing)"}
        sound_candidates = [
            "/usr/share/sounds/alsa/Front_Center.wav",
            "/usr/share/sounds/alsa/Rear_Center.wav"
        ]
        for s in sound_candidates:
            if os.path.exists(s):
                if background:
                    background.add_task(playsound, s)
                else:
                    try:
                        playsound(s)
                    except Exception:
                        pass
                return {"module": "Entertainment", "action": "play_music", "file": s}
        return {"module": "Entertainment", "action": "play_music", "note": "no system sound found"}
    if "game" in t or "adventure" in t:
        story = (
            "You wake up in a dimly lit room. There is a door to the north and a window to the east. "
            "Type 'go north' or 'look window' to continue. (This is a stateless demo; extend for sessions.)"
        )
        return {"module": "Entertainment", "action": "text_adventure", "story": story}
    if "trivia" in t:
        q = {"question": "What is the capital of Kenya?", "choices": ["Nairobi", "Mombasa", "Kisumu"], "answer": "Nairobi"}
        return {"module": "Entertainment", "action": "trivia", "question": q}
    return {"status": "unknown", "module": "Entertainment", "text": text}

# ---------------------------
# Module: Finance (expense logging, crypto placeholder)
# ---------------------------
def finance_handle(text: str):
    t = text.lower()
    if "expense" in t or re.search(r'\bspent\b|\bpay\b|\bpaid\b', t):
        m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]{2,4})?', text)
        if m:
            amount = float(m.group(1))
            currency = m.group(2) if m.group(2) else "USD"
        else:
            amount = 0.0
            currency = "USD"
        category = "general"
        note = text
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO expenses (ts,amount,currency,category,note) VALUES (?,?,?,?,?)",
                    (datetime.utcnow().isoformat(), amount, currency, category, note))
        conn.commit()
        conn.close()
        result = {"module": "Finance", "action": "expense_logged", "amount": amount, "currency": currency}
        log_event("Finance", text, result)
        return result
    if "crypto" in t or "bitcoin" in t or "btc" in t:
        return {"module": "Finance", "action": "crypto_prices", "BTC": "placeholder: integrate API"}
    return {"status": "unknown", "module": "Finance", "text": text}

# ---------------------------
# Module: Knowledge (placeholder)
# ---------------------------
def knowledge_handle(text: str):
    return {
        "module": "Knowledge",
        "action": "search_placeholder",
        "note": "Integrate search API to fetch live facts and summaries."
    }

# ---------------------------
# Dispatcher
# ---------------------------
class CommandIn(BaseModel):
    text: str

@app.post("/command")
def command_endpoint(payload: CommandIn, background_tasks: BackgroundTasks):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty command")
    t = text.lower()
    try:
        if any(k in t for k in ["remind", "reminder", "task", "todo"]):
            res = productivity_handle(text)
        elif any(k in t for k in ["scan", "nmap", "phishing", "network"]):
            res = security_handle(text)
        elif any(k in t for k in ["ocr", "convert", "calculate", "export", "csv"]):
            res = utilities_handle(text)
        elif any(k in t for k in ["play", "music", "game", "trivia", "adventure"]):
            res = entertainment_handle(text, background=background_tasks)
        elif any(k in t for k in ["expense", "spent", "paid", "crypto", "bitcoin", "btc"]):
            res = finance_handle(text)
        elif any(k in t for k in ["search", "summarize", "news", "who", "what", "when", "where", "why"]):
            res = knowledge_handle(text)
        else:
            res = {"module": "General", "action": "unrecognized", "text": text}
        log_event("Dispatcher", text, res)
        return {"status": "ok", "response": res}
    except Exception as e:
        log_event("Dispatcher", text, {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------
# File upload endpoint for OCR
# ---------------------------
@app.post("/ocr-upload")
async def ocr_upload(file: UploadFile = File(...)):
    if not _HAS_OCR:
        return {"status": "error", "error": "OCR not available; install pytesseract and tesseract-ocr"}
    tmp_path = os.path.join("/tmp", f"ocr_{int(time.time())}_{file.filename}")
    with open(tmp_path, "wb") as f:
        f.write(await file.read())
    try:
        img = Image.open(tmp_path)
        text = pytesseract.image_to_string(img)
        log_event("Utilities", f"ocr-upload {file.filename}", {"text": text})
        return {"status": "ok", "text": text}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ---------------------------
# Health and admin endpoints
# ---------------------------
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get("/logs")
def get_logs(limit: int = 50):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id,ts,module,command,result FROM logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return {"count": len(rows), "rows": rows}

# ---------------------------
# Startup message
# ---------------------------
@app.on_event("startup")
def startup_event():
    console.print("[bold green]Text-First Super-App started[/bold green]")
    console.print("[yellow]Endpoints: POST /command  POST /ocr-upload  GET /health  GET /logs[/yellow]")
    console.print("[cyan]Open http://127.0.0.1:8000/docs to interact via Swagger UI[/cyan"])

