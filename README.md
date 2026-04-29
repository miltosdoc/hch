# Hjärtcentrum Halland (HCH) Integrations

This repository contains the software ecosystem for **Hjärtcentrum Halland**, facilitating integration with the Webdoc API, managing Holter examinations, parsing PDFs, and archiving ECG data.

## 🚀 Services Overview

The ecosystem consists of four main microservices/applications, all of which can be started simultaneously using the master script.

### 1. Integrationsportalen (WebdocAPI)
- **Role:** The core Flask application managing Webdoc API communications. Handles document uploads, OCR-based patient data extraction from PDFs, and automated booking synchronization.
- **Port:** `5000`
- **Tech Stack:** Python, Flask
- **Key Features:**
  - Automated patient lookups and creation via SPAR/Webdoc.
  - OCR extraction for referral dates and phone numbers.
  - Generates patient statistics and booking reports.

### 2. Pulsus Holter Tracker
- **Role:** A tracking and scheduling system for Holter monitors.
- **Location:** `Holter Flow/`
- **Port:** `8080`
- **Tech Stack:** Docker, React (Frontend), Node/Python (Backend)
- **Key Features:**
  - Intelligent booking workflow with real-time slot availability.
  - Device assignment and tracking list.

### 3. EKG Arkiv
- **Role:** A lightweight file server/viewer for ECG archive files.
- **Location:** `ECG-Viewer/`
- **Port:** `8085`
- **Tech Stack:** PowerShell HTTP Server, HTML/JS
- **Key Features:**
  - Fast, local access to ECG records.
  - Runs silently in the background.

### 4. Holter Review
- **Role:** An interface for reviewing and refining Holter report data before final submission.
- **Location:** `Holter Review/`
- **Port:** `8086`
- **Tech Stack:** Python, Flask
- **Key Features:**
  - High-fidelity markdown rendering for generated reports.
  - Edit/preview toggles with plain-text copy functionality.

---

## 🛠️ How to Run

### Master Start Script
To start all services at once, run the `start_all_services.bat` script located in the root directory.

```cmd
start_all_services.bat
```

This script will:
1. Wait for Docker Desktop to be ready.
2. Launch **Pulsus Holter Tracker** via Docker Compose (`http://localhost:8080`).
3. Launch **Integrationsportalen** in the background (`http://localhost:5000`).
4. Launch **EKG Arkiv** in the background (`http://localhost:8085`).
5. Launch **Holter Review** in the background (`http://localhost:8086`).

### Prerequisites
- **Python 3.x**
- **Docker Desktop** (required for Pulsus Holter Tracker)
- **PowerShell** (required for EKG Arkiv)

---

## 🔐 Credentials & Security

> **Note:** API credentials and sensitive patient data are strictly excluded from this repository via `.gitignore`. 

To run the Integrationsportalen locally, you must provide your Webdoc API credentials in `docs/api.txt` or configure them via environment variables depending on the script being used.

Format for `docs/api.txt`:
```text
ClientID: YOUR_CLIENT_ID
Secret: YOUR_CLIENT_SECRET
```
