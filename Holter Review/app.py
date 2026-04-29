"""
Holter Review — Flask Backend
PDF processing, AI report generation, and patient data management.
"""

import os
import re
import json
import sqlite3
import shutil
import threading
import time
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file, send_from_directory
import requests as http_requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
INCOMING_DIR = BASE_DIR / "Incoming"
ARKIV_DIR = BASE_DIR / "Arkiv"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "holter_review.db"
USERS_PATH = BASE_DIR.parent / "data" / "users.json"

INCOMING_DIR.mkdir(exist_ok=True)
ARKIV_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "openai_api_url": "",
            "openai_api_key": "",
            "openai_model": "gpt-4o",
            "port": 8086,
        }

config = load_config()

# ---------------------------------------------------------------------------
# Flask App
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.urandom(24)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_filename TEXT UNIQUE NOT NULL,
            patient_name TEXT DEFAULT '',
            personnummer TEXT DEFAULT '',
            extracted_text TEXT DEFAULT '',
            generated_report TEXT DEFAULT '',
            edited_report TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_reports_filename ON reports(pdf_filename);
    """)
    # Seed default prompt if not exists
    existing = conn.execute("SELECT value FROM settings WHERE key = 'prompt_template'").fetchone()
    if not existing:
        default_prompt = (
            "Du är en erfaren kardiolog. Analysera följande Holter-undersökningsrapport och "
            "skapa ett strukturerat utlåtande (medicinsk bedömning) på svenska. "
            "Inkludera:\n"
            "1. Undersökningsdata (registreringslängd, analyserad tid)\n"
            "2. Grundrytm och frekvens\n"
            "3. Supraventrikulära arytmier\n"
            "4. Ventrikulära arytmier\n"
            "5. Pauser och överledningsstörningar\n"
            "6. ST-förändringar\n"
            "7. Sammanfattning och bedömning\n\n"
            "Rapport:\n{text}"
        )
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('prompt_template', ?)",
            (default_prompt,),
        )
    conn.commit()
    conn.close()


init_db()

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def get_users():
    try:
        with open(USERS_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"admin": "123456"}


def check_auth(req):
    cookie = req.cookies.get("HolterReviewAuth")
    return cookie == "true"

# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------
def extract_text_from_pdf(filepath):
    """Extract text from a PDF. Try PyMuPDF first, fall back to OCR if needed."""
    text = ""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(filepath))
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
    except Exception as e:
        print(f"PyMuPDF extraction failed: {e}")

    # If very little text extracted, try OCR
    if len(text.strip()) < 50:
        try:
            import fitz
            doc = fitz.open(str(filepath))
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")

                # Use pytesseract for OCR on the image
                try:
                    from PIL import Image
                    import pytesseract
                    import io

                    img = Image.open(io.BytesIO(img_data))
                    ocr_text = pytesseract.image_to_string(img, lang="swe+eng")
                    text += ocr_text + "\n"
                except ImportError:
                    print("pytesseract/Pillow not available for OCR fallback")
                    break
            doc.close()
        except Exception as e:
            print(f"OCR fallback also failed: {e}")

    return text.strip()


def extract_patient_info(text):
    """Extract patient name and personnummer from Holter report text.
    
    Expected format (Hjärtcentrum Halland Holter Report):
        Patient Info
        Name:    Philip Alexandersson    Gender:  Male    Age:  36 Years
        Ordering Department:  Pulsus Hem-EKG   Serial No:  260213000023
    """
    personnummer = None
    patient_name = None

    # Try to find personnummer: 191212121212 or 19121212-1212
    pnr_patterns = [
        r'((?:19|20)\d{6}-\d{4})',       # 19121212-1212
        r'((?:19|20)\d{10})',              # 191212121212
        r'(\d{6}-\d{4})',                  # 121212-1212
    ]
    for pattern in pnr_patterns:
        match = re.search(pattern, text)
        if match:
            personnummer = match.group(1)
            # Normalize: ensure 12 digits with dash
            digits = personnummer.replace("-", "")
            if len(digits) == 10:
                year_part = int(digits[:2])
                century = "19" if year_part > 26 else "20"
                digits = century + digits
            if len(digits) == 12:
                personnummer = digits[:8] + "-" + digits[8:]
            break

    # Try to find patient name — specific patterns for Holter reports
    # Supports both colon-separated (Name: ...) and whitespace-separated (Namn   ...)
    name_patterns = [
        # "Name: Philip Alexandersson  Gender:" — stop at known field labels
        r'(?:Name|Namn)\s*[:;]\s*(.+?)(?:\s{2,}|\t|Gender|Kön|Serial|Ordering|Beställ|Födelse|\n)',
        # Cortrium format: "Namn\nAnita Olofsson\nFödelsedatum" (label on own line, value on next)
        r'(?:^|\n)Namn\s*\n([^\n]+?)(?:\n|$)',
        # Cortrium format: "Namn        Anita Olofsson" (tab/multi-space separated on same line)
        r'(?:^|\n)\s*Namn\s{2,}([A-ZÀ-Öa-zà-ö][A-ZÀ-Öa-zà-ö ]+?)(?:\s{2,}|\t|Födelse|Kön|Pacemaker|\n|$)',
        # "Patientnamn: Philip Alexandersson" on its own line
        r'(?:Patientnamn|Patient\s*namn)\s*[:;]?\s*(.+?)(?:\s{2,}|\t|\n|$)',
        # "Pat: Philip Alexandersson" or "Pat.: ..."
        r'(?:Pat\.?)\s*[:;]\s*(.+?)(?:\s{2,}|\t|Gender|Kön|\n|$)',
        # Generic fallback: "Name" or "Namn" followed by whitespace then a name
        r'(?:Name|Namn)\s+([A-ZÀ-Ö][a-zà-ö]+\s+[A-ZÀ-Ö][a-zà-ö]+(?:\s+[A-ZÀ-Ö][a-zà-ö]+)?)',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name_candidate = match.group(1).strip()
            # Clean up: remove excess whitespace, limit length
            name_candidate = " ".join(name_candidate.split())
            # Filter out obviously wrong matches (single words, all-caps headers, etc.)
            if (3 <= len(name_candidate) <= 60 
                and name_candidate.lower() not in ("info", "patient info", "patient", "info age")
                and not name_candidate.isdigit()):
                patient_name = name_candidate
                break

    return patient_name, personnummer


def anonymize_text(text, patient_name, personnummer):
    """Remove patient-identifying information from text."""
    anonymized = text
    if personnummer:
        # Remove both formats
        pnr_digits = personnummer.replace("-", "")
        anonymized = anonymized.replace(personnummer, "[PERSONNUMMER]")
        anonymized = anonymized.replace(pnr_digits, "[PERSONNUMMER]")
        # Also try with different dash formats
        if len(pnr_digits) == 12:
            anonymized = anonymized.replace(
                pnr_digits[:8] + "-" + pnr_digits[8:], "[PERSONNUMMER]"
            )
    if patient_name:
        anonymized = anonymized.replace(patient_name, "[PATIENT]")
        # Also try individual name parts
        for part in patient_name.split():
            if len(part) > 2:
                anonymized = anonymized.replace(part, "[PATIENT]")
    return anonymized


# ---------------------------------------------------------------------------
# PDF Processing Pipeline
# ---------------------------------------------------------------------------
def process_incoming_pdfs():
    """Process all PDFs in the Incoming folder."""
    results = []
    incoming_files = list(INCOMING_DIR.glob("*.pdf")) + list(INCOMING_DIR.glob("*.PDF"))

    for pdf_path in incoming_files:
        try:
            # Extract text
            text = extract_text_from_pdf(pdf_path)
            patient_name, personnummer = extract_patient_info(text)

            # Generate unique filename for arkiv
            arkiv_filename = pdf_path.name
            arkiv_path = ARKIV_DIR / arkiv_filename

            # Handle duplicates
            counter = 1
            while arkiv_path.exists():
                stem = pdf_path.stem
                arkiv_filename = f"{stem}_{counter}{pdf_path.suffix}"
                arkiv_path = ARKIV_DIR / arkiv_filename
                counter += 1

            # Move to Arkiv
            shutil.move(str(pdf_path), str(arkiv_path))

            # Save to database
            conn = get_db()
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO reports
                       (pdf_filename, patient_name, personnummer, extracted_text, created_at, updated_at)
                       VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))""",
                    (arkiv_filename, patient_name or "", personnummer or "", text),
                )
                conn.commit()
            finally:
                conn.close()

            results.append({
                "filename": arkiv_filename,
                "patient_name": patient_name or "Ej identifierad",
                "personnummer": personnummer or "Ej hittat",
                "text_length": len(text),
            })
        except Exception as e:
            results.append({
                "filename": pdf_path.name,
                "error": str(e),
            })

    return results

# ---------------------------------------------------------------------------
# Routes — Static files
# ---------------------------------------------------------------------------
@app.route("/")
@app.route("/index.html")
def serve_index():
    return send_file(str(BASE_DIR / "index.html"))


@app.route("/logoofficial.png")
def serve_logo():
    return send_file(str(BASE_DIR / "logoofficial.png"))


@app.route("/style.css")
def serve_css():
    return send_file(str(BASE_DIR / "style.css"), mimetype="text/css")

# ---------------------------------------------------------------------------
# Routes — Auth
# ---------------------------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    users = get_users()

    if username in users and users[username] == password:
        resp = jsonify({"success": True})
        resp.set_cookie("HolterReviewAuth", "true", path="/")
        return resp
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    resp = jsonify({"success": True})
    resp.set_cookie("HolterReviewAuth", "", expires=0, path="/")
    return resp

# ---------------------------------------------------------------------------
# Routes — Files & PDFs
# ---------------------------------------------------------------------------
@app.route("/api/files")
def api_files():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    rows = conn.execute(
        "SELECT pdf_filename, patient_name, personnummer, created_at FROM reports ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    # Also include any PDFs in Arkiv that aren't in the database yet
    db_files = {r["pdf_filename"] for r in rows}
    result = []

    for r in rows:
        pdf_path = ARKIV_DIR / r["pdf_filename"]
        size = pdf_path.stat().st_size if pdf_path.exists() else 0
        result.append({
            "filename": r["pdf_filename"],
            "patient_name": r["patient_name"],
            "personnummer": r["personnummer"],
            "created_at": r["created_at"],
            "size": size,
        })

    # Check for unprocessed files in Arkiv
    for pdf_path in sorted(ARKIV_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True):
        if pdf_path.name not in db_files:
            result.append({
                "filename": pdf_path.name,
                "patient_name": "",
                "personnummer": "",
                "created_at": datetime.fromtimestamp(pdf_path.stat().st_mtime).isoformat(),
                "size": pdf_path.stat().st_size,
            })

    return jsonify(result)


@app.route("/api/pdf")
def api_pdf():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    name = request.args.get("name")
    if not name:
        return jsonify({"error": "Missing name parameter"}), 400

    pdf_path = ARKIV_DIR / name
    if not pdf_path.exists():
        return jsonify({"error": "File not found"}), 404

    return send_file(str(pdf_path), mimetype="application/pdf")


@app.route("/api/incoming_count")
def api_incoming_count():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    count = len(list(INCOMING_DIR.glob("*.pdf")) + list(INCOMING_DIR.glob("*.PDF")))
    return jsonify({"count": count})

# ---------------------------------------------------------------------------
# Routes — Processing
# ---------------------------------------------------------------------------
@app.route("/api/process", methods=["POST"])
def api_process():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    results = process_incoming_pdfs()
    return jsonify({"success": True, "processed": results})

# ---------------------------------------------------------------------------
# Routes — AI Report Generation
# ---------------------------------------------------------------------------
@app.route("/api/generate", methods=["POST"])
def api_generate():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "Missing filename"}), 400

    # Get report data from DB
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM reports WHERE pdf_filename = ?", (filename,)
    ).fetchone()

    if not row:
        conn.close()
        return jsonify({"error": "Report not found in database"}), 404

    extracted_text = row["extracted_text"]
    patient_name = row["patient_name"]
    personnummer = row["personnummer"]

    # Get prompt template
    prompt_row = conn.execute(
        "SELECT value FROM settings WHERE key = 'prompt_template'"
    ).fetchone()
    conn.close()

    prompt_template = prompt_row["value"] if prompt_row else "Analysera denna rapport:\n{text}"

    # Anonymize the text
    anonymized = anonymize_text(extracted_text, patient_name, personnummer)

    # Build the prompt
    prompt = prompt_template.replace("{text}", anonymized)

    # Call OpenAI-compatible API
    try:
        api_url = config.get("openai_api_url", "")
        api_key = config.get("openai_api_key", "")
        model = config.get("openai_model", "gpt-4o")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Du är en erfaren kardiolog som skriver medicinska utlåtanden på svenska."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 4000,
        }

        response = http_requests.post(api_url, headers=headers, json=payload, timeout=120)

        if response.status_code == 200:
            result = response.json()
            generated_text = result["choices"][0]["message"]["content"]

            # Save generated report
            conn = get_db()
            conn.execute(
                "UPDATE reports SET generated_report = ?, edited_report = ?, updated_at = datetime('now') WHERE pdf_filename = ?",
                (generated_text, generated_text, filename),
            )
            conn.commit()
            conn.close()

            return jsonify({"success": True, "report": generated_text})
        else:
            return jsonify({
                "success": False,
                "error": f"API error {response.status_code}: {response.text}",
            }), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ---------------------------------------------------------------------------
# Routes — Reports
# ---------------------------------------------------------------------------
@app.route("/api/report")
def api_get_report():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    filename = request.args.get("name")
    if not filename:
        return jsonify({"error": "Missing name"}), 400

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM reports WHERE pdf_filename = ?", (filename,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Not found"}), 404

    return jsonify({
        "filename": row["pdf_filename"],
        "patient_name": row["patient_name"],
        "personnummer": row["personnummer"],
        "extracted_text": row["extracted_text"],
        "generated_report": row["generated_report"],
        "edited_report": row["edited_report"],
        "created_at": row["created_at"],
    })


@app.route("/api/report", methods=["POST"])
def api_save_report():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    filename = data.get("filename")
    edited_report = data.get("edited_report", "")

    if not filename:
        return jsonify({"error": "Missing filename"}), 400

    conn = get_db()
    conn.execute(
        "UPDATE reports SET edited_report = ?, updated_at = datetime('now') WHERE pdf_filename = ?",
        (edited_report, filename),
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True})

# ---------------------------------------------------------------------------
# Routes — Prompt Template
# ---------------------------------------------------------------------------
@app.route("/api/prompt")
def api_get_prompt():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = 'prompt_template'").fetchone()
    conn.close()

    return jsonify({"prompt": row["value"] if row else ""})


@app.route("/api/prompt", methods=["POST"])
def api_save_prompt():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    prompt = data.get("prompt", "")

    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('prompt_template', ?)",
        (prompt,),
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True})

# ---------------------------------------------------------------------------
# Downloads Folder Watcher
# ---------------------------------------------------------------------------
# UUID pattern: 8 hex chars - 4 - 4 - 4 - 12 hex chars .pdf
UUID_PDF_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.pdf$',
    re.IGNORECASE
)

def get_downloads_folder():
    """Get the user's Downloads folder (works on Windows)."""
    # Try the standard Windows Downloads path
    downloads = Path.home() / "Downloads"
    if downloads.exists():
        return downloads
    # Try Swedish name
    hamtade = Path.home() / "Hämtade filer"
    if hamtade.exists():
        return hamtade
    return None


def watch_downloads_folder(interval=10):
    """Background thread: poll Downloads folder for UUID-named PDFs
    and move them to the Incoming folder."""
    downloads = get_downloads_folder()
    if not downloads:
        print("[Watcher] Could not find Downloads folder, watcher disabled.")
        return

    print(f"[Watcher] Monitoring {downloads} for Holter PDFs (UUID filenames)...")

    while True:
        try:
            for pdf_path in downloads.glob("*.pdf"):
                if UUID_PDF_PATTERN.match(pdf_path.name):
                    # Wait a moment to ensure the file is fully downloaded
                    try:
                        initial_size = pdf_path.stat().st_size
                        time.sleep(1)
                        if not pdf_path.exists():
                            continue
                        if pdf_path.stat().st_size != initial_size:
                            continue  # Still downloading
                        if initial_size == 0:
                            continue  # Empty file
                    except OSError:
                        continue

                    dest = INCOMING_DIR / pdf_path.name
                    if not dest.exists():
                        try:
                            shutil.move(str(pdf_path), str(dest))
                            print(f"[Watcher] Moved {pdf_path.name} → Incoming/")
                        except Exception as e:
                            print(f"[Watcher] Error moving {pdf_path.name}: {e}")
        except Exception as e:
            print(f"[Watcher] Error scanning downloads: {e}")

        time.sleep(interval)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = config.get("port", 8086)

    # Start Downloads folder watcher in background
    watcher_thread = threading.Thread(target=watch_downloads_folder, daemon=True)
    watcher_thread.start()

    print(f"Holter Review starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
