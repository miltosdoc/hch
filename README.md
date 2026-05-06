# Hjärtcentrum Halland (HCH) — Integration Ecosystem

Unified platform for Hjärtcentrum Halland (HCH) and Pulsus Hem-EKG: patient data ingestion, WebDoc API integration, Holter monitor management, and ECG archival.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Nginx Reverse Proxy (port 8080 / 8081)                │
│  Routes: /portal → :5001   /holter-review → :5002       │
│           /holter-tracker → :5003   /ecg-archive → :5004 │
└──────────┬──────────────────┬─────────────────┬─────────┘
           │                  │                 │
     ┌─────▼─────┐    ┌──────▼──────┐   ┌──────▼──────┐
     │   Portal   │    │ Holter      │   │   ECG       │
     │  :5001     │    │ Review      │   │ Archive     │
     │            │    │ :5002       │   │  :5004      │
     │ Login,     │    │ Upload,     │   │ Upload,     │
     │ Admin,     │    │ OCR,        │   │ Store,      │
     │ Stats,     │    │ Reports     │   │ Retrieve    │
     │ Scan Bot   │    │             │   │             │
     └─────┬──────┘    └─────────────┘   └──────┬──────┘
           │                                      │
     ┌─────▼──────┐                        ┌─────▼──────┐
     │ Holter     │                        │ PostgreSQL │
     │ Tracker    │                        │ :5432      │
     │ :5003      │                        │            │
     │ Devices,   │                        └────────────┘
     │ Bookings,  │
     │ WebDoc Sync│
     └────────────┘
           │
     ┌─────▼──────┐
     │   Redis    │
     │   :6379    │
     │ (Sessions) │
     └────────────┘
```

## Services

### 1. Portal (`app/` — port 5001)
The central application handling authentication, patient data, and statistics.

**Features:**
- User authentication (login/logout, admin dashboard)
- API key management (create, revoke, list keys — used by external systems)
- Patient data ingestion via file upload (PDF, JPG, PNG, TIFF) — auto-extracts Swedish personal numbers (personnummer) via OCR
- Batch upload support for multiple files at once
- Statistics dashboard — waiting time analysis (referral-to-booking, vårdgaranti-to-booking)
- CSV export of patient data
- Scanned file history

**API endpoints:**
- `POST /api/auth/token` — exchange username/password for API key
- `POST /api/scan/upload` — upload single file for OCR
- `POST /api/scan/batch` — upload multiple files
- `GET /api/patients` — list patients (with date filters)
- `GET /api/statistics/summary` — get stats
- `GET /api/export/csv` — download CSV export
- `PUT /api/patient/<pn>/update` — update patient dates
- `POST /api/patient/<pn>/toggle` — toggle återbesök status
- `DELETE /api/patient/<pn>` — delete patient record

### 2. Holter Review (`holter-review/` — port 5002)
Upload and process Holter ECG reports.

**Features:**
- PDF upload with automatic text extraction
- Swedish personal number extraction from uploaded files
- Patient name and exam date extraction
- HTML report generation with extracted data
- Report listing and detail view

**API endpoints:**
- `POST /upload` — upload Holter PDF report
- `GET /api/list` — list reports
- `GET /api/report/<id>` — get report details

### 3. Holter Tracker (`holter-tracker/` — port 5003)
Device and booking management for Holter monitors.

**Features:**
- Device management (add devices, track status: available/assigned)
- Booking scheduling (add bookings with patient, date, time, device)
- WebDoc API sync placeholder (WebDoc integration pending)
- Device assignment tracking

**API endpoints:**
- `GET /api/devices` — list devices
- `POST /api/devices/add` — add device
- `POST /api/devices/<serial>/status` — update device status
- `GET /api/bookings` — list bookings (with date filters)
- `POST /api/bookings/add` — add booking
- `POST /api/sync` — WebDoc sync (placeholder)

### 4. ECG Archive (`ecg-archive/` — port 5004)
Store and retrieve ECG files.

**Features:**
- Upload ECG files (PDF, JPG, PNG, TIFF, DICOM)
- File storage with patient metadata (personal number, name, exam date)
- Retrieve files by ID
- File listing

**API endpoints:**
- `POST /upload` — upload ECG file
- `GET /file/<id>` — retrieve file
- `GET /api/list` — list archived files

## Shared Infrastructure

### Database (PostgreSQL 15)
Shared across all services. Tables:
- `hch_users` — user accounts
- `api_keys` — API key management
- `patients` — patient records (shared by Portal + Holter Tracker)
- `scanned_files` — scan bot upload history
- `holter_reports` — Holter review reports
- `holter_devices` — Holter device inventory
- `holter_bookings` — Holter booking records
- `ecg_archive` — ECG file records

### Redis
Session storage (Flask sessions via `flask-session`).

### Nginx
Reverse proxy routing to all services. Also serves the `/health` monitoring endpoint on port 8081.

## Authentication

All services use a shared authentication system:
- **Session-based login** for web UI (Portal handles auth)
- **API key-based auth** for programmatic access — keys are created in the Portal admin dashboard or via `POST /api/auth/token`
- **CSRF protection** on all HTML forms (1-hour token limit)
- **Session expiry** (1 hour)

## Docker Compose Services

| Service | Port | Description |
|---------|------|-------------|
| `db` | 5432 | PostgreSQL database |
| `redis` | 6379 | Redis session store |
| `portal` | 5001 | Portal app |
| `holter-review` | 5002 | Holter Review app |
| `holter-tracker` | 5003 | Holter Tracker app |
| `ecg-archive` | 5004 | ECG Archive app |
| `nginx` | 8080/8081 | Reverse proxy / health endpoint |

## Quick Start

```bash
# 1. Configure
cp .env.example .env
# Edit .env — set SECRET_KEY and ADMIN_PASSWORD

# 2. Start
docker compose up -d --build

# 3. Verify
curl http://localhost:8081/health
```

## HTTPS Setup

See [DEPLOY.md](DEPLOY.md) for full HTTPS configuration with Let's Encrypt.

## Backup

```bash
docker compose exec db pg_dump -U hch_user hch > backup.sql
```

## Security

- Never commit `.env` to git (it's in `.gitignore`)
- Change the default admin password after first login
- Use HTTPS in production (see DEPLOY.md)
- Rotate `SECRET_KEY` if you suspect a leak
- Regular database backups
- Update Docker images regularly: `docker compose pull && docker compose up -d`

## Project Structure

```
hch/
├── app/                  # Portal service (port 5001)
│   ├── Dockerfile
│   ├── app.py            # Flask app — auth, admin, stats, scan bot
│   ├── database.py       # Shared DB hooks
│   ├── doc_parser.py     # PDF OCR parsing
│   ├── health.py         # /health endpoint
│   └── templates/        # HTML templates
│
├── holter-review/        # Holter Review service (port 5002)
│   ├── Dockerfile
│   ├── app.py            # Flask app — upload, OCR, reports
│   ├── health.py         # /health endpoint
│   └── templates/
│
├── holter-tracker/       # Holter Tracker service (port 5003)
│   ├── Dockerfile
│   ├── app.py            # Flask app — devices, bookings
│   ├── health.py         # /health endpoint
│   └── templates/
│
├── ecg-archive/          # ECG Archive service (port 5004)
│   ├── Dockerfile
│   ├── app.py            # Flask app — file storage
│   ├── health.py         # /health endpoint
│   └── templates/
│
├── shared/               # Shared code (all services)
│   ├── __init__.py
│   ├── db.py             # PostgreSQL schema + CRUD functions
│   ├── auth.py           # Auth decorators + API helpers
│   └── db_hooks.py       # Connection pool hooks
│
├── nginx/                # Nginx reverse proxy config
│   ├── default.conf
│   └── health.conf       # /health endpoint config
│
├── docker-compose.yml    # Orchestration
├── DEPLOY.md             # Production deployment guide
├── .env.example          # Environment variable template
└── .gitignore            # Excludes .env, uploads, etc.
```
