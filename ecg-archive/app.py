"""ECG Archive - Store and view ECG PDFs."""
import os, sys, re
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, g
from flask_session import Session
from redis import Redis

sys.path.insert(0, "/app")
from shared.db import init_all, get_pool, teardown, log_ecg, get_ecgs, get_ecg

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "hch-dev-key")
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
Session(app)

ECG_DIR = Path("/app/ecgs")
ECG_DIR.mkdir(parents=True, exist_ok=True)

@app.teardown_appcontext
def close(e=None): teardown(e)

@app.context_processor
def portal_ctx():
    return {"portal_url": os.environ.get("PORTAL_URL", "")}

@app.before_request
def init():
    with app.app_context(): init_all()

def find_pnr(text):
    m = re.search(r'((?:19|20)\d{6})[-+]?\d{4}', text)
    if m: return m.group(0)
    m = re.search(r'(\d{6})[-+](\d{4})', text)
    if m:
        c = "20" if int(m.group(1)[:2])<50 else "19"
        return f"{c}{m.group(1)}-{m.group(2)}"
    return None

@app.route("/")
def archive():
    return render_template("index.html", ecgs=get_ecgs(200))

@app.route("/upload", methods=["POST"])
def ecg_upload():
    f = request.files.get("file")
    if not f: return jsonify({"ok":False,"msg":"Ingen fil"}), 400
    fn = f.filename or "ecg.pdf"
    pnr = request.form.get("pnr","") or find_pnr(fn) or ""
    name = request.form.get("name","")
    edate = request.form.get("exam_date","") or datetime.now().strftime("%Y-%m-%d")
    saved = ECG_DIR / fn
    f.save(str(saved))
    log_ecg(fn, pnr, name, edate, str(saved))
    return jsonify({"ok":True,"msg":"Sparad","pn":pnr})

@app.route("/file/<int:eid>")
def ecg_file(eid):
    r = get_ecg(eid)
    if r and r["file_path"] and os.path.exists(r["file_path"]):
        return send_file(r["file_path"])
    return jsonify({"ok":False}), 404

@app.route("/api/list")
def api_list():
    return jsonify([dict(e) for e in get_ecgs(200)])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
