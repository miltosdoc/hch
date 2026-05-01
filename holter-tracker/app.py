"""Holter Tracker - Device management + WebDoc bookings."""
import os, sys
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_session import Session
from redis import Redis

sys.path.insert(0, "/app")
from shared.db import init_all, get_pool, teardown, add_device, get_devices, set_device_status, get_bookings, add_booking

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "hch-dev-key")
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
Session(app)

@app.teardown_appcontext
def close(e=None): teardown(e)

@app.context_processor
def portal_ctx():
    return {"portal_url": os.environ.get("PORTAL_URL", "")}

@app.before_request
def init():
    with app.app_context(): init_all()

# --- ROUTES ---
@app.route("/")
def tracker():
    return render_template("index.html", devices=get_devices(), bookings=get_bookings())

@app.route("/api/devices")
def api_devices():
    return jsonify([dict(d) for d in get_devices()])

@app.route("/api/devices/add", methods=["POST"])
def api_add_device():
    d = request.get_json()
    add_device(d.get("serial",""), d.get("type","Lepu"))
    return jsonify({"ok":True})

@app.route("/api/devices/<serial>/status", methods=["PUT"])
def api_device_status(serial):
    d = request.get_json()
    set_device_status(serial, d.get("status"), d.get("patient"), d.get("assigned_date"))
    return jsonify({"ok":True})

@app.route("/api/bookings")
def api_bookings():
    sd = request.args.get("start")
    ed = request.args.get("end")
    return jsonify([dict(b) for b in get_bookings(sd, ed)])

@app.route("/api/bookings/add", methods=["POST"])
def api_add_booking():
    d = request.get_json()
    add_booking(d.get("pnr"), d.get("name",""), d.get("booking_date"),
                d.get("start_time",""), d.get("end_time",""),
                d.get("device",""), d.get("notes",""))
    return jsonify({"ok":True})

# --- WebDoc sync ---
@app.route("/api/sync", methods=["POST"])
def api_sync():
    """Pull bookings from WebDoc API - placeholder for now."""
    return jsonify({"ok":True,"msg":"Sync placeholder - add WebDoc API key"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
