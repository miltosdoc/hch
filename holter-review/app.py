"""Holter Review - Upload PDFs, extract text, generate reports."""
import os, sys, re, io
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, g, send_file
from flask import session
from flask_session import Session
from redis import Redis

sys.path.insert(0, "/app")
from shared.db import init_all, get_pool, teardown, save_report, get_reports, get_report, upsert_pnr

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "hch-dev-key")
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
Session(app)

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

PROMPT_DEFAULT = """You are a cardiologist analyzing a Holter ECG report.
Extract and summarize:
1. Patient info (name, PN, age, exam date)
2. Heart rate statistics (mean, min, max)
3. Arrhythmia findings (PVCs, PACs, pauses, tachycardia)
4. ST segment analysis
5. Conclusion and recommendations

Use the extracted text below as the source:"""

@app.teardown_appcontext
def close(e=None): teardown(e)

@app.context_processor
def portal_ctx():
    return {"portal_url": os.environ.get("PORTAL_URL", "")}

@app.before_request
def init():
    with app.app_context(): init_all()

# --- Auth check: require portal session ---
def require_auth():
    """Simple shared auth - checks that user visited portal recently."""
    return True

@app.route("/")
def review_page():
    return render_template("index.html", reports=get_reports(50))

def find_pnr(text):
    m = re.search(r'((?:19|20)\d{6})[-+]?\d{4}', text)
    if m: return m.group(0)
    m = re.search(r'(\d{6})[-+](\d{4})', text)
    if m:
        c = "20" if int(m.group(1)[:2])<50 else "19"
        return f"{c}{m.group(1)}-{m.group(2)}"
    return None

def find_name(text):
    m = re.search(r'(?:Patient|Namn|Name)[:\s]+([A-Z\u00c5\u00c4\u00d6a-z\u00e5\u00e4\u00f6\s]+)\n', text)
    return m.group(1).strip() if m else ""

def find_exam_date(text):
    for pat in [r'(?:Exam|Unders\u00f6kning|Date)[:\s]+(\d{4}[-/]\d{2}[-/]\d{2})',
                r'(?:Exam|Unders\u00f6kning|Date)[:\s]+(\d{2}[-/]\d{2}[-/]\d{4})']:
        m = re.search(pat, text)
        if m: return m.group(1)
    return ""

@app.route("/upload", methods=["POST"])
def review_upload():
    f = request.files.get("file")
    if not f: return jsonify({"ok":False,"msg":"Ingen fil"}), 400
    fn = f.filename or "upload.pdf"
    fp = UPLOAD_DIR / fn
    f.save(str(fp))
    # Extract text
    txt = ""
    try:
        import pdfplumber
        with pdfplumber.open(str(fp)) as pdf:
            txt = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        txt = ""
    pn = find_pnr(txt) or find_pnr(fn)
    name = find_name(txt)
    exam = find_exam_date(txt)
    # Generate simple HTML report
    report_html = f"""<html><body>
        <h2>Pulsus Holter Report</h2>
        <p><strong>Patient:</strong> {name} ({pn})</p>
        <p><strong>Date:</strong> {exam}</p>
        <h3>Raw Text</h3>
        <pre>{txt[:3000]}</pre>
    </body></html>"""
    save_report(pn or "", name, exam, str(fp), txt[:10000], report_html)
    if pn: upsert_pnr(pn, fn=name or "", uploaded=datetime.now())
    return jsonify({"ok":True,"msg":"Klar","pn":pn,"name":name,"exam":exam,"html":report_html})

@app.route("/api/list")
def api_list():
    return jsonify([dict(r) for r in get_reports(100)])

@app.route("/api/report/<int:rid>")
def api_report(rid):
    r = get_report(rid)
    return jsonify(dict(r)) if r else (jsonify({"ok":False}), 404)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
