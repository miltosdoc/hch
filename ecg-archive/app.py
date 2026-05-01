"""ECG Archive - Store and retrieve ECG PDFs."""
import os, sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, g, send_file
from flask import session
from flask_session import Session
from redis import Redis
from werkzeug.utils import secure_filename

sys.path.insert(0, "/app")
from shared.db import init_all, get_pool, teardown, log_ecg, get_ecgs, get_ecg
from shared.auth import require_auth, api_response, api_error

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "hch-dev-key")
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
app.config["SESSION_COOKIE_NAME"] = "hch_session"
app.config["SESSION_COOKIE_PATH"] = "/"
Session(app)

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.teardown_appcontext
def close(e=None): teardown(e)

@app.context_processor
def portal_ctx():
    return {"portal_url": os.environ.get("PORTAL_URL", "")}

@app.before_request
def init():
    with app.app_context(): init_all()

@app.route("/")
@require_auth
def archive_page():
    return render_template("index.html", ecgs=get_ecgs(200))

@app.route("/upload", methods=["POST"])
@require_auth
def upload_ecg():
    f = request.files.get("file")
    if not f: return api_error("bad_request", "Ingen fil"), 400
    fn = secure_filename(f.filename)
    fp = UPLOAD_DIR / fn
    f.save(str(fp))
    pnr = request.form.get("personal_number", "")
    name = request.form.get("patient_name", "")
    edate = request.form.get("exam_date", "")
    log_ecg(fn, pnr or "", name, edate or "", str(fp))
    return api_response({"ok": True, "filename": fn})

@app.route("/file/<int:eid>")
@require_auth
def get_file(eid):
    r = get_ecg(eid)
    if not r: return api_error("not_found", "File not found"), 404
    fp = r["file_path"]
    if os.path.exists(fp):
        return send_file(fp, mimetype="application/pdf")
    return api_error("not_found", "File missing on disk"), 404

@app.route("/api/list")
@require_auth
def api_list():
    return api_response([dict(e) for e in get_ecgs(200)])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
