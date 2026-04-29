"""
SQLite Database Layer for Webdoc Patient Tracking.

Stores patient data with referral dates, vårdgaranti dates,
and booking sync metadata.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, date

# Path adjusts to point to ../data/webdoc_patients.db
DB_PATH = Path(__file__).parent.parent / "data" / "webdoc_patients.db"

def get_db():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personal_number TEXT UNIQUE NOT NULL,
            first_name TEXT DEFAULT '',
            last_name TEXT DEFAULT '',
            phone_number TEXT DEFAULT '',
            referral_date TEXT,
            vardgaranti_date TEXT,
            first_booking_date TEXT,
            uploaded_at TEXT,
            is_aterbesok INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type TEXT NOT NULL,
            last_synced_date TEXT NOT NULL,
            synced_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS bot_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personal_number TEXT NOT NULL,
            file_names TEXT NOT NULL,
            error_message TEXT NOT NULL,
            error_type TEXT DEFAULT 'upload',
            resolved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            resolved_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_patients_pn ON patients(personal_number);
        CREATE INDEX IF NOT EXISTS idx_bot_errors_resolved ON bot_errors(resolved);
    """)
    
    # Migration: add is_aterbesok column if missing
    try:
        conn.execute("ALTER TABLE patients ADD COLUMN is_aterbesok INTEGER DEFAULT 0")
        conn.commit()
    except:
        pass  # Column already exists
    
    conn.commit()
    conn.close()


def upsert_patient(personal_number, first_name=None, last_name=None,
                   phone_number=None, referral_date=None, vardgaranti_date=None,
                   first_booking_date=None, uploaded_at=None):
    """Insert or update a patient record. Only updates non-None fields."""
    conn = get_db()
    existing = conn.execute(
        "SELECT * FROM patients WHERE personal_number = ?", (personal_number,)
    ).fetchone()

    if existing:
        updates = []
        params = []
        if first_name is not None:
            updates.append("first_name = ?")
            params.append(first_name)
        if last_name is not None:
            updates.append("last_name = ?")
            params.append(last_name)
        if phone_number is not None:
            updates.append("phone_number = ?")
            params.append(phone_number)
        if referral_date is not None:
            updates.append("referral_date = ?")
            params.append(referral_date)
        if vardgaranti_date is not None:
            updates.append("vardgaranti_date = ?")
            params.append(vardgaranti_date)
        if first_booking_date is not None:
            # Only update if earlier than existing or existing is null
            existing_fbd = existing['first_booking_date']
            if existing_fbd is None or first_booking_date < existing_fbd:
                updates.append("first_booking_date = ?")
                params.append(first_booking_date)

        if uploaded_at is not None:
            updates.append("uploaded_at = ?")
            params.append(uploaded_at)

        if updates:
            updates.append("updated_at = datetime('now')")
            params.append(personal_number)
            conn.execute(
                f"UPDATE patients SET {', '.join(updates)} WHERE personal_number = ?",
                params
            )
    else:
        conn.execute(
            """INSERT INTO patients 
               (personal_number, first_name, last_name, phone_number, referral_date, vardgaranti_date, first_booking_date, uploaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (personal_number, first_name or '', last_name or '', phone_number or '',
             referral_date, vardgaranti_date, first_booking_date, uploaded_at)
        )

    conn.commit()
    conn.close()


def update_patient_dates(personal_number, referral_date=None, vardgaranti_date=None):
    """Update only the date fields for a patient."""
    conn = get_db()
    updates = ["updated_at = datetime('now')"]
    params = []

    if referral_date is not None:
        updates.append("referral_date = ?")
        params.append(referral_date if referral_date != '' else None)
    if vardgaranti_date is not None:
        updates.append("vardgaranti_date = ?")
        params.append(vardgaranti_date if vardgaranti_date != '' else None)

    params.append(personal_number)
    conn.execute(
        f"UPDATE patients SET {', '.join(updates)} WHERE personal_number = ?",
        params
    )
    conn.commit()
    conn.close()


def get_all_patients():
    """Return all patients as list of dicts."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM patients ORDER BY uploaded_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_patient(personal_number):
    """Return a single patient by personnummer."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM patients WHERE personal_number = ?", (personal_number,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_last_sync_date(sync_type="bookings"):
    """Get the last successfully synced date."""
    conn = get_db()
    row = conn.execute(
        "SELECT last_synced_date FROM sync_log WHERE sync_type = ? ORDER BY synced_at DESC LIMIT 1",
        (sync_type,)
    ).fetchone()
    conn.close()
    return row['last_synced_date'] if row else None


def set_last_sync_date(sync_type, last_date):
    """Record a successful sync."""
    conn = get_db()
    conn.execute(
        "INSERT INTO sync_log (sync_type, last_synced_date) VALUES (?, ?)",
        (sync_type, last_date)
    )
    conn.commit()
    conn.close()


def get_patient_count():
    """Return total patient count."""
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as cnt FROM patients").fetchone()
    conn.close()
    return row['cnt']


def delete_patient(personal_number):
    """Delete a patient by personnummer."""
    conn = get_db()
    conn.execute("DELETE FROM patients WHERE personal_number = ?", (personal_number,))
    conn.commit()
    conn.close()


def toggle_aterbesok(personal_number):
    """Toggle the is_aterbesok flag for a patient. Returns the new value."""
    conn = get_db()
    row = conn.execute(
        "SELECT is_aterbesok FROM patients WHERE personal_number = ?", (personal_number,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    new_val = 0 if row['is_aterbesok'] else 1
    conn.execute(
        "UPDATE patients SET is_aterbesok = ?, updated_at = datetime('now') WHERE personal_number = ?",
        (new_val, personal_number)
    )
    conn.commit()
    conn.close()
    return new_val


# ---------------------------------------------------------
# BOT ERROR LOGGING
# ---------------------------------------------------------

def log_bot_error(personal_number, file_names, error_message, error_type='upload'):
    """Log a watcher bot error for later review in the UI."""
    import json
    conn = get_db()
    conn.execute(
        """INSERT INTO bot_errors (personal_number, file_names, error_message, error_type)
           VALUES (?, ?, ?, ?)""",
        (personal_number, json.dumps(file_names), error_message, error_type)
    )
    conn.commit()
    conn.close()


def get_bot_errors(resolved=False):
    """Return bot errors as list of dicts."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM bot_errors WHERE resolved = ? ORDER BY created_at DESC",
        (1 if resolved else 0,)
    ).fetchall()
    conn.close()
    import json
    results = []
    for r in rows:
        d = dict(r)
        try:
            d['file_names'] = json.loads(d['file_names'])
        except:
            d['file_names'] = [d['file_names']]
        results.append(d)
    return results


def get_bot_error_count():
    """Return count of unresolved bot errors."""
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as cnt FROM bot_errors WHERE resolved = 0").fetchone()
    conn.close()
    return row['cnt']


def get_bot_error(error_id):
    """Return a single bot error by ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM bot_errors WHERE id = ?", (error_id,)).fetchone()
    conn.close()
    if row:
        import json
        d = dict(row)
        try:
            d['file_names'] = json.loads(d['file_names'])
        except:
            d['file_names'] = [d['file_names']]
        return d
    return None


def resolve_bot_error(error_id):
    """Mark a bot error as resolved."""
    conn = get_db()
    conn.execute(
        "UPDATE bot_errors SET resolved = 1, resolved_at = datetime('now') WHERE id = ?",
        (error_id,)
    )
    conn.commit()
    conn.close()


def delete_bot_error(error_id):
    """Delete a bot error record."""
    conn = get_db()
    conn.execute("DELETE FROM bot_errors WHERE id = ?", (error_id,))
    conn.commit()
    conn.close()

