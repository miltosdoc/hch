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
    create_api_key, validate_api_key, list_api_keys, revoke_api_key, delete_api_key,
)
from shared.auth import require_auth, require_admin, api_response, api_error

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "hch-dev-key")
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
app.config["SESSION_COOKIE_NAME"] = "hch_session"
app.config["SESSION_COOKIE_PATH"] = "/"
Session(app)

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)

class U(UserMixin):
    def __init__(self, id_, username, is_admin):
        self.id = id_; self.username = username; self.is_admin = is_admin

@login_manager.user_loader
def load(uid):
    try:
        uid_int = int(uid)
    except (ValueError, TypeError):
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
        error = "Fel användarnamn eller lösenord"
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

# --- ADMIN ---
@app.route("/admin")
@login_required
def admin_page():
    if not getattr(current_user, "is_admin", False):
        return redirect(url_for("dashboard"))
    keys = list_api_keys(current_user.id) if current_user.is_admin else []
    return render_template("admin.html", users=list_users(), api_keys=keys)

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
    if uid and pw: reset_password(int(uid), pw); flash("Lösenord återställt", "ok")
    return redirect(url_for("admin_page"))

@app.route("/admin/toggle", methods=["POST"])
@login_required
def admin_toggle():
    if not current_user.is_admin: return redirect(url_for("admin_page"))
    if request.form.get("user_id"): toggle_user(int(request.form["user_id"]))
    return redirect(url_for("admin_page"))

# --- API KEY MANAGEMENT ---
@app.route("/admin/api-key/create", methods=["POST"])
@login_required
def admin_create_api_key():
    if not current_user.is_admin: return redirect(url_for("admin_page"))
    name = request.form.get("name", "").strip()
    plain, _ = create_api_key(current_user.id, name)
    flash(f"API-nyckel skapad: {plain} — Spara den nu, den visas inte igen!", "ok")
    return redirect(url_for("admin_page"))

@app.route("/admin/api-key/revoke/<int:key_id>", methods=["POST"])
@login_required
def admin_revoke_api_key(key_id):
    if not current_user.is_admin: return redirect(url_for("admin_page"))
    revoke_api_key(key_id, current_user.id)
    flash("API-nyckel inaktiverad", "ok")
    return redirect(url_for("admin_page"))

@app.route("/admin/api-key/delete/<int:key_id>", methods=["POST"])
@login_required
def admin_delete_api_key(key_id):
    if not current_user.is_admin: return redirect(url_for("admin_page"))
    delete_api_key(key_id, current_user.id)
    flash("API-nyckel raderad", "ok")
    return redirect(url_for("admin_page"))

# --- API AUTH ENDPOINT ---
@app.route("/api/auth/token", methods=["POST"])
def api_auth_token():
    """Exchange username/password for an API key token."""
    data = request.get_json()
    if not data:
        return api_error("bad_request", "JSON body required"), 400
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return api_error("bad_request", "username and password required"), 400
    
    user = verify_user(username, password)
    if not user:
        return api_error("unauthorized", "Invalid credentials"), 401
    
    plain, _ = create_api_key(user["id"], f"{username}-cli")
    return api_response({"token": plain, "username": username, "expires": "never"})

# --- SCANNER ---
@app.route("/scanner")
@login_required
def scanner():
    return render_template("scanner.html")

@app.route("/api/scan/upload", methods=["POST"])
@require_auth
def scan_upload():
    f = request.files.get("file")
    if not f or f.filename=="": return api_error("bad_request", "Ingen fil"), 400
    fn = secure_filename(f.filename)
    fp = UPLOAD_DIR / fn
    f.save(str(fp))
    pn = find_pnr(fn)
    ref_d, vg_d, ocr_ok = None, None, False
    if fn.lower().endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(str(fp)) as pdf:
                txt = "\n".join(p.extract_text() or "" for p in pdf.pages)
            ocr_ok = bool(txt)
            if not pn and txt: pn = find_pnr(txt)
        except: pass
    if not pn: return api_error("not_found", "Hittade inget personnummer"), 400
    upsert_pnr(pn, ref=ref_d, vg=vg_d, uploaded=datetime.now())
    log_scan(fn, pn, ref_d, vg_d, ocr_ok)
    return api_response({"ok":True,"msg":"Klar","pn":pn})

@app.route("/api/scan/batch", methods=["POST"])
@require_auth
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
    return api_response({"results": results})

# --- STATISTICS ---
@app.route("/statistics")
@login_required
def statistics():
    return render_template("statistics.html")

@app.route("/api/patients")
@require_auth
def api_patients():
    ft = request.args.get("filter_type","first_booking_date")
    ps = get_patients(ft,
        request.args.get("start") or None,
        request.args.get("end") or None,
        request.args.get("mode",""))
    return api_response([dict(p) for p in ps])

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
@require_auth
def api_stats():
    ps = get_patients()
    sr, sv = calc_stats(ps)
    return api_response({"total": len(ps), "referral": sr, "vardgaranti": sv})

@app.route("/api/patient/<pn>", methods=["DELETE"])
@require_admin
def api_del(pn):
    delete_pnr(pn)
    return api_response({"ok":True})

@app.route("/api/patient/<pn>/toggle", methods=["POST"])
@require_auth
def api_toggle(pn):
    toggle_ater(pn)
    return api_response({"ok":True})

@app.route("/api/patient/<pn>/update", methods=["PUT"])
@require_auth
def api_update(pn):
    d = request.get_json()
    update_dates(pn, d.get("referral_date"), d.get("vardgaranti_date"))
    return api_response({"ok":True})

@app.route("/api/scanned_files")
@require_auth
def api_scanned():
    return api_response([dict(f) for f in get_scanned(100)])

@app.route("/api/export/csv")
@require_auth
def api_export():
    ps = get_patients()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["PN","Förnamn","Efternamn","Uppladdad","Remiss","Vårdgaranti","Bokning"])
    for p in ps: w.writerow([p.get("personal_number",""),p.get("first_name",""),p.get("last_name",""),str(p.get("uploaded_at","")),str(p.get("referral_date","")),str(p.get("vardgaranti_date","")),str(p.get("first_booking_date",""))])
    out.seek(0)
    resp = make_response(out.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    resp.headers["Content-Disposition"] = "attachment; filename=stats.csv"
    return resp

if __name__ == "__main__":
    with app.app_context(): init_all()
