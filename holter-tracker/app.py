"""Holter Tracker - Device management, bookings, WebDoc sync."""
import os, sys, json, re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, g
from flask import session
from flask_session import Session
from redis import Redis

sys.path.insert(0, "/app")
from shared.db import init_all, get_pool, teardown, get_devices, add_device, set_device_status, get_bookings, add_booking
from shared.auth import require_auth, require_admin, api_response, api_error

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "hch-dev-key")
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
app.config["SESSION_COOKIE_NAME"] = "hch_session"
app.config["SESSION_COOKIE_PATH"] = "/"
Session(app)

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
def tracker_page():
    devices = get_devices()
    bookings = get_bookings()
    return render_template("index.html", devices=devices, bookings=bookings)

@app.route("/api/devices")
@require_auth
def api_devices():
    return api_response([dict(d) for d in get_devices()])

@app.route("/api/devices/add", methods=["POST"])
@require_admin
def api_add_device():
    data = request.get_json()
    serial = data.get("serial", "").strip()
    dtype = data.get("type", "Lepu")
    if not serial:
        return api_error("bad_request", "Serial required"), 400
    try:
        add_device(serial, dtype)
        return api_response({"ok": True, "serial": serial})
    except Exception as e:
        return api_error("db_error", str(e)), 500

@app.route("/api/devices/<serial>/status", methods=["POST"])
@require_auth
def api_device_status(serial):
    data = request.get_json()
    status = data.get("status", "")
    patient = data.get("patient")
    adate = data.get("assigned_date")
    set_device_status(serial, status, patient, adate)
    return api_response({"ok": True, "serial": serial, "status": status})

@app.route("/api/bookings")
@require_auth
def api_bookings():
    sd = request.args.get("start")
    ed = request.args.get("end")
    return api_response([dict(b) for b in get_bookings(sd, ed)])

@app.route("/api/bookings/add", methods=["POST"])
@require_auth
def api_add_booking():
    data = request.get_json()
    pnr = data.get("personal_number", "").strip()
    name = data.get("patient_name", "")
    bdate = data.get("booking_date", "")
    st = data.get("start_time", "")
    et = data.get("end_time", "")
    dev = data.get("device_serial", "")
    notes = data.get("notes", "")
    if not pnr or not bdate:
        return api_error("bad_request", "personal_number and booking_date required"), 400
    add_booking(pnr, name, bdate, st, et, dev, notes)
    return api_response({"ok": True})

@app.route("/api/sync", methods=["POST"])
@require_admin
def api_sync():
    """Placeholder for WebDoc API sync."""
    return api_response({"ok": True, "synced": 0, "note": "WebDoc sync not yet implemented"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
