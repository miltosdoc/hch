"""Portal - Login, Admin, Dashboard, Scan Bot, Statistics."""
import os, re, io, csv, sys
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, g, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_session import Session
from redis import Redis
from werkzeug.utils import secure_filename

sys.path.insert(0, "/app")
from shared.db import (
    verify_user, get_user, list_users, create_user, reset_password, toggle_user,
    upsert_pnr, get_patients, get_patient_row, delete_pnr, toggle_ater, update_dates,
    log_scan, get_scanned, init_all, get_pool, teardown as _teardown,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "hch-dev-key")
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_PATH"] = "/"
app.config["SESSION_COOKIE_NAME"] = "hch_session"
Session(app)

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

lm = LoginManager()
lm.init_app(app)
lm.login_view = "login"

class U(UserMixin):
    def __init__(self, uid, un, ia):
        self.id = uid; self.username = un; self.is_admin = ia

@lm.user_loader
def load(uid):
    # Handle both numeric IDs (new sessions) and usernames (old sessions)
    try:
        uid_int = int(uid)
    except (ValueError, TypeError):
        # uid is a username string from old session — look it up
        r = get_user_by_username(str(uid))
        return U(r["id"], r["username"], r["is_admin"]) if r else None
    r = get_user(uid_int)
    return U(r["id"], r["username"], r["is_admin"]) if r else None

@app.teardown_appcontext
def close(exception=None):
    _teardown()

@app.before_request
def init():
    with app.app_context():
        init_all()

def find_pnr(text):
    m = re.search(r'((?:19|20)\d{6})[-+]?\d{4}', text)
    if m: return m.group(0)[:4]+"-"+m.group(0)[4:13] if len(m.group(0))==12 else m.group(0)
    m = re.search(r'(\d{6})[-+](\d{4})', text)
    if m:
        c = "20" if int(m.group(1)[:2])<50 else "19"
        return f"{c}{m.group(1)}-{m.group(2)}"
    return None

# --- ROUTES ---
@app.route("/")
def index():
    return redirect(url_for("dashboard") if current_user.is_authenticated else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        u = verify_user(request.form["username"].strip(), request.form["password"])
        if u:
            login_user(U(u["id"], u["username"], u["is_admin"]), remember=True)
            return redirect(url_for("dashboard"))
        error = "Fel anv\u00e4ndarnamn eller l\u00f6senord"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    logout_user()
    session.pop('session', None)
    resp = redirect(url_for("login"))
    resp.delete_cookie("hch_session", path="/", domain=None)
    resp.delete_cookie("session", path="/", domain=None)
    return resp

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/admin")
@login_required
def admin_page():
    if not getattr(current_user, "is_admin", False):
        return redirect(url_for("dashboard"))
    return render_template("admin.html", users=list_users())

@app.route("/admin/create", methods=["POST"])
@login_required
def admin_create():
    if not current_user.is_admin: return redirect(url_for("admin_page"))
    un, pw = request.form.get("username","").strip(), request.form.get("password","")
    dn = request.form.get("display_name","").strip()
    ia = request.form.get("is_admin") == "on"
    if un and pw:
        try: create_user(un, pw, dn, ia); flash(f"Skapad: {un}", "ok")
        except: flash(f"Misslyckades", "err")
    return redirect(url_for("admin_page"))

@app.route("/admin/reset", methods=["POST"])
@login_required
def admin_reset():
    if not current_user.is_admin: return redirect(url_for("admin_page"))
    uid, pw = request.form.get("user_id"), request.form.get("new_password")
    if uid and pw: reset_password(int(uid), pw); flash("L%C3%B6senord %C3%A5terst%C3%A4llt", "ok")
    return redirect(url_for("admin_page"))

@app.route("/admin/toggle", methods=["POST"])
@login_required
def admin_toggle():
    if not current_user.is_admin: return redirect(url_for("admin_page"))
    if request.form.get("user_id"): toggle_user(int(request.form["user_id"]))
    return redirect(url_for("admin_page"))

# --- SCANNER ---
@app.route("/scanner")
@login_required
def scanner():
    return render_template("scanner.html")

@app.route("/api/scan/upload", methods=["POST"])
@login_required
def scan_upload():
    f = request.files.get("file")
    if not f or f.filename=="": return jsonify({"ok":False,"msg":"Ingen fil"}), 400
    fn = secure_filename(f.filename)
    fp = UPLOAD_DIR / fn
    f.save(str(fp))
    pn = find_pnr(fn)
    # Try OCR for dates from PDF
    ref_d, vg_d, ocr_ok = None, None, False
    if fn.lower().endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(str(fp)) as pdf:
                txt = "\n".join(p.extract_text() or "" for p in pdf.pages)
            ocr_ok = bool(txt)
            if not pn and txt: pn = find_pnr(txt)
        except: pass
    if not pn: return jsonify({"ok":False,"msg":"Hittade inget personnummer"}), 400
    upsert_pnr(pn, ref=ref_d, vg=vg_d, uploaded=datetime.now())
    log_scan(fn, pn, ref_d, vg_d, ocr_ok)
    return jsonify({"ok":True,"msg":"Klar","pn":pn})

@app.route("/api/scan/batch", methods=["POST"])
@login_required
def scan_batch():
    files = request.files.getlist("file")
    results = []
    for f in files:
        fn = secure_filename(f.filename)
        fp = UPLOAD_DIR / fn
        f.save(str(fp))
        pn = find_pnr(fn)
        if pn:
            upsert_pnr(pn, uploaded=datetime.now())
            log_scan(fn, pn)
            results.append({"file": fn, "pn": pn})
    return jsonify({"ok":True,"results":results})

# --- STATISTICS ---
@app.route("/statistics")
@login_required
def statistics():
    return render_template("statistics.html")

@app.route("/api/patients")
@login_required
def api_patients():
    ft = request.args.get("filter_type","first_booking_date")
    ps = get_patients(ft,
        request.args.get("start") or None,
        request.args.get("end") or None,
        request.args.get("mode",""))
    return jsonify([dict(p) for p in ps])

def calc_stats(patients):
    wr, wv = [], []
    for p in patients:
        fbd = p.get("first_booking_date"); rd = p.get("referral_date"); vg = p.get("vardgaranti_date")
        if isinstance(fbd, datetime): fbd = fbd.strftime("%Y-%m-%d")
        if isinstance(rd, datetime): rd = rd.strftime("%Y-%m-%d")
        if isinstance(vg, datetime): vg = vg.strftime("%Y-%m-%d")
        try:
            if fbd and rd: wr.append((datetime.strptime(fbd,"%Y-%m-%d") - datetime.strptime(rd,"%Y-%m-%d")).days)
            if fbd and vg: wv.append((datetime.strptime(fbd,"%Y-%m-%d") - datetime.strptime(vg,"%Y-%m-%d")).days)
        except: pass
    def s(v):
        if not v: return {"mean":0,"median":0,"count":0,"under_90_pct":0}
        vs=sorted(v); n=len(vs); med=vs[n//2] if n%2 else (vs[n//2-1]+vs[n//2])/2
        return {"mean":round(sum(vs)/n,1),"median":round(med,1),"count":n,"under_90_pct":round(sum(1 for x in vs if x<=90)/n*100,1)}
    return s(wr), s(wv)

@app.route("/api/statistics/summary")
@login_required
def api_stats():
    ps = get_patients()
    sr, sv = calc_stats(ps)
    return jsonify({"total": len(ps), "referral": sr, "vardgaranti": sv})

@app.route("/api/patient/<pn>", methods=["DELETE"])
@login_required
def api_del(pn):
    delete_pnr(pn)
    return jsonify({"ok":True})

@app.route("/api/patient/<pn>/toggle", methods=["POST"])
@login_required
def api_toggle(pn):
    toggle_ater(pn)
    return jsonify({"ok":True})

@app.route("/api/patient/<pn>/update", methods=["PUT"])
@login_required
def api_update(pn):
    d = request.get_json()
    update_dates(pn, d.get("referral_date"), d.get("vardgaranti_date"))
    return jsonify({"ok":True})

@app.route("/api/scanned_files")
@login_required
def api_scanned():
    return jsonify([dict(f) for f in get_scanned(100)])

@app.route("/api/export/csv")
@login_required
def api_export():
    ps = get_patients()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["PN","F\u00f6rnamn","Efternamn","Uppladdad","Remiss","V\u00e5rdgaranti","Bokning"])
    for p in ps: w.writerow([p.get("personal_number",""),p.get("first_name",""),p.get("last_name",""),str(p.get("uploaded_at","")),str(p.get("referral_date","")),str(p.get("vardgaranti_date","")),str(p.get("first_booking_date",""))])
    out.seek(0)
    resp = make_response(out.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    resp.headers["Content-Disposition"] = "attachment; filename=stats.csv"
    return resp

if __name__ == "__main__":
    with app.app_context(): init_all()
    app.run(host="0.0.0.0", port=5000)
