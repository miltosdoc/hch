"""Shared PostgreSQL database layer for all HCH apps."""
import os, json
from datetime import datetime
from contextlib import contextmanager
from flask import g
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

_POOL = None

def get_pool():
    global _POOL
    if _POOL is None:
        _POOL = pool.ThreadedConnectionPool(1, 20, os.environ["DATABASE_URL"])
    return _POOL

def get_db():
    if "db" not in g or g.get("db_closed", True):
        conn = get_pool().getconn()
        conn.autocommit = True
        g.db = conn
        g.db_closed = False
    return g["db"]

@contextmanager
def cur():
    c = get_db().cursor(cursor_factory=RealDictCursor)
    try:
        yield c
    finally:
        c.close()

def exec(sql, params=None):
    with cur() as c:
        c.execute(sql, params)
        return c.fetchall() if c.description else None

def row(sql, params=None):
    with cur() as c:
        c.execute(sql, params)
        return c.fetchone()

# ---------- INIT TABLES ----------
def init_all():
    get_db()  # ensure connection
    # USERS
    exec("""CREATE TABLE IF NOT EXISTS hch_users (
        id SERIAL PRIMARY KEY, username VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(200) NOT NULL, display_name VARCHAR(100) DEFAULT '',
        is_admin BOOLEAN DEFAULT FALSE, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT NOW())""")
    # Create default admin
    r = row("SELECT COUNT(*) c FROM hch_users")
    if r and r["c"] == 0:
        exec("INSERT INTO hch_users (username, password_hash, display_name, is_admin) VALUES (%s,%s,%s,%s)",
             ("admin", generate_password_hash("admin"), "Administrator", True))

    # PATIENTS (shared - scan bot + tracker)
    exec("""CREATE TABLE IF NOT EXISTS patients (
        id SERIAL PRIMARY KEY, personal_number VARCHAR(15) UNIQUE NOT NULL,
        first_name VARCHAR(120) DEFAULT '', last_name VARCHAR(120) DEFAULT '',
        phone VARCHAR(30), referral_date DATE, vardgaranti_date DATE,
        first_booking_date DATE, uploaded_at TIMESTAMP,
        is_aterbesok BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW())""")

    # SCANNED FILES
    exec("""CREATE TABLE IF NOT EXISTS scanned_files (
        id SERIAL PRIMARY KEY, filename VARCHAR(500), personal_number VARCHAR(15),
        referral_date DATE, vardgaranti_date DATE, ocr_success BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW())""")

    # HOLTER REPORTS
    exec("""CREATE TABLE IF NOT EXISTS holter_reports (
        id SERIAL PRIMARY KEY, patient_pnr VARCHAR(15), patient_name VARCHAR(250),
        exam_date VARCHAR(50), pdf_path VARCHAR(500), raw_text TEXT,
        report_html TEXT, created_at TIMESTAMP DEFAULT NOW())""")

    # HOLTER DEVICES + BOOKINGS
    exec("""CREATE TABLE IF NOT EXISTS holter_devices (
        id SERIAL PRIMARY KEY, device_serial VARCHAR(50) UNIQUE NOT NULL,
        device_type VARCHAR(50) DEFAULT 'Lepu', status VARCHAR(20) DEFAULT 'available',
        assigned_patient VARCHAR(100), assigned_date DATE, return_date DATE,
        notes TEXT, created_at TIMESTAMP DEFAULT NOW())""")

    exec("""CREATE TABLE IF NOT EXISTS holter_bookings (
        id SERIAL PRIMARY KEY, personal_number VARCHAR(15), patient_name VARCHAR(250),
        booking_date DATE, start_time VARCHAR(10), end_time VARCHAR(10),
        device_serial VARCHAR(50), webdoc_booking_id VARCHAR(100),
        status VARCHAR(30) DEFAULT 'scheduled', notes TEXT, created_at TIMESTAMP DEFAULT NOW())""")

    # ECG ARCHIVE
    exec("""CREATE TABLE IF NOT EXISTS ecg_archive (
        id SERIAL PRIMARY KEY, filename VARCHAR(500), personal_number VARCHAR(15),
        patient_name VARCHAR(250), exam_date DATE, file_path VARCHAR(500),
        created_at TIMESTAMP DEFAULT NOW())""")

# ---------- USER CRUD ----------
def verify_user(username, password):
    u = row("SELECT * FROM hch_users WHERE username=%s AND is_active", (username,))
    return u if u and check_password_hash(u["password_hash"], password) else None

def get_user(uid):
    return row("SELECT * FROM hch_users WHERE id=%s", (uid,))

def list_users():
    return exec("SELECT * FROM hch_users ORDER BY id")

def create_user(username, password, display_name="", is_admin=False):
    exec("INSERT INTO hch_users (username, password_hash, display_name, is_admin) VALUES (%s,%s,%s,%s)",
         (username, generate_password_hash(password), display_name, is_admin))

def reset_password(uid, pw):
    exec("UPDATE hch_users SET password_hash=%s WHERE id=%s", (generate_password_hash(pw), uid))

def toggle_user(uid):
    exec("UPDATE hch_users SET is_active=NOT is_active WHERE id!=1 AND id=%s", (uid,))

# ---------- PATIENT CRUD ----------
def upsert_pnr(pnr, fn=None, ln=None, phone=None, ref=None, vg=None, booking=None, uploaded=None):
    r = row("SELECT id FROM patients WHERE personal_number=%s", (pnr,))
    if r:
        exec("UPDATE patients SET first_name=COALESCE(%s,first_name),last_name=COALESCE(%s,last_name),referral_date=COALESCE(%s,referral_date),vardgaranti_date=COALESCE(%s,vardgaranti_date),uploaded_at=COALESCE(%s,uploaded_at) WHERE personal_number=%s",
             (fn, ln, ref, vg, uploaded, pnr))
    else:
        exec("INSERT INTO patients (personal_number,first_name,last_name,phone,referral_date,vardgaranti_date,first_booking_date,uploaded_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
             (pnr, fn or '', ln or '', phone or '', ref, vg, booking, uploaded))

def get_patients(ft="first_booking_date", sd=None, ed=None, mode="", no_ater=True):
    q = "SELECT * FROM patients WHERE 1=1"
    p = []
    if no_ater: q += " AND NOT is_aterbesok"
    if mode == "incoming": q += " AND (referral_date IS NOT NULL OR vardgaranti_date IS NOT NULL)"
    if sd: q += f" AND {ft}>=%s"; p.append(sd)
    if ed: q += f" AND {ft}<=%s"; p.append(ed)
    q += " ORDER BY created_at DESC"
    return exec(q, p)

def get_patient_row(pnr):
    return row("SELECT * FROM patients WHERE personal_number=%s", (pnr,))

def delete_pnr(pnr):
    exec("DELETE FROM patients WHERE personal_number=%s", (pnr,))

def toggle_ater(pnr):
    r = row("SELECT is_aterbesok FROM patients WHERE personal_number=%s", (pnr,))
    if r:
        nv = not r["is_aterbesok"]
        exec("UPDATE patients SET is_aterbesok=%s WHERE personal_number=%s", (nv, pnr))
        return nv

def update_dates(pnr, ref=None, vg=None):
    exec("UPDATE patients SET referral_date=COALESCE(%s,referral_date),vardgaranti_date=COALESCE(%s,vardgaranti_date) WHERE personal_number=%s", (ref, vg, pnr))

# ---------- SCANNED ----------
def log_scan(fn, pnr, ref=None, vg=None, ocr=False):
    exec("INSERT INTO scanned_files (filename,personal_number,referral_date,vardgaranti_date,ocr_success) VALUES (%s,%s,%s,%s,%s)",
         (fn, pnr, ref, vg, ocr))

def get_scanned(n=100):
    return exec("SELECT * FROM scanned_files ORDER BY created_at DESC LIMIT %s", (n,))

# ---------- HOLTER REPORTS ----------
def save_report(pnr, name, exam, path, text, html):
    exec("INSERT INTO holter_reports (patient_pnr,patient_name,exam_date,pdf_path,raw_text,report_html) VALUES (%s,%s,%s,%s,%s,%s)",
         (pnr, name, exam, path, text, html))

def get_reports(n=100):
    return exec("SELECT * FROM holter_reports ORDER BY created_at DESC LIMIT %s", (n,))

def get_report(id_):
    return row("SELECT * FROM holter_reports WHERE id=%s", (id_,))

# ---------- HOLTER DEVICES ----------
def add_device(serial, dtype="Lepu"):
    exec("INSERT INTO holter_devices (device_serial,device_type) VALUES (%s,%s)", (serial, dtype))

def get_devices():
    return exec("SELECT * FROM holter_devices ORDER BY device_serial")

def set_device_status(serial, status, patient=None, adate=None):
    if status == "available":
        exec("UPDATE holter_devices SET status=%s,assigned_patient=NULL,assigned_date=NULL WHERE device_serial=%s", (status, serial))
    else:
        exec("UPDATE holter_devices SET status=%s,assigned_patient=%s,assigned_date=%s WHERE device_serial=%s", (status, patient, adate, serial))

def get_bookings(sd=None, ed=None):
    q = "SELECT * FROM holter_bookings WHERE 1=1"
    p = []
    if sd: q += " AND booking_date>=%s"; p.append(sd)
    if ed: q += " AND booking_date<=%s"; p.append(ed)
    q += " ORDER BY booking_date"
    return exec(q, p)

def add_booking(pnr, name, bdate, st="", et="", dev="", notes=""):
    exec("INSERT INTO holter_bookings (personal_number,patient_name,booking_date,start_time,end_time,device_serial,notes) VALUES (%s,%s,%s,%s,%s,%s,%s)",
         (pnr, name, bdate, st, et, dev, notes))

# ---------- ECG ARCHIVE ----------
def log_ecg(fn, pnr, name, edate, path):
    exec("INSERT INTO ecg_archive (filename,personal_number,patient_name,exam_date,file_path) VALUES (%s,%s,%s,%s,%s)",
         (fn, pnr, name, edate, path))

def get_ecgs(n=200):
    return exec("SELECT * FROM ecg_archive ORDER BY created_at DESC LIMIT %s", (n,))

def get_ecg(id_):
    return row("SELECT * FROM ecg_archive WHERE id=%s", (id_,))

# ---------- CLEANUP ----------
def teardown(exception=None):
    db = g.pop("db", None)
    if db:
        try: get_pool().putconn(db)
        except: pass
        g.db_closed = True
