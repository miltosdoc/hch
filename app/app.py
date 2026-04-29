import os
import json
import re
import shutil
from pathlib import Path
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests as http_requests
from werkzeug.utils import secure_filename
from PIL import Image
import database as db
from doc_parser import parse_document

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database on startup
db.init_db()

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    users = get_users()
    if user_id in users:
        return User(user_id)
    return None

def get_users():
    try:
        users_path = Path(__file__).parent.parent / "data" / "users.json"
        with open(users_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"admin": "123456"}

# ---------------------------------------------------------
# WEBDOC API INTEGRATION
# ---------------------------------------------------------
class WebdocClient:
    def __init__(self):
        self.client_id, self.client_secret = self._load_credentials()
        self.auth_url = "https://auth.atlan.se"
        self.base_url = "https://api.atlan.se"
        self.access_token = None

    def _load_credentials(self):
        try:
            api_path = Path(__file__).parent.parent / "docs" / "api.txt"
            with open(api_path, 'r', encoding='utf-8') as f:
                content = f.read()
                client_id = re.search(r'ClientID:\s*(.+)', content).group(1).strip()
                secret = re.search(r'Secret:\s*(.+)', content).group(1).strip()
                return client_id, secret
        except Exception as e:
            print(f"Error loading api.txt: {e}")
            return None, None

    def authenticate(self):
        if not self.client_id or not self.client_secret:
            return False, "Missing credentials"
            
        token_endpoint = f"{self.auth_url}/oauth/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "documents:write patient:read patient:write document-types:read clinics:read users:read bookings:read bookings:write patient-types:read actioncodes:read"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            response = http_requests.post(token_endpoint, data=data, headers=headers)
            if response.status_code == 200:
                self.access_token = response.json().get("access_token")
                return True, "Success"
            else:
                return False, f"Auth failed: {response.text}"
        except Exception as e:
            return False, str(e)

    def get_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    def ensure_auth(self):
        if not self.access_token:
            self.authenticate()

    def get_document_types(self):
        self.ensure_auth()
        try:
            response = http_requests.get(f"{self.base_url}/v1/documentTypes", headers=self.get_headers())
            return response.json() if response.status_code == 200 else []
        except:
            return []

    def get_clinics(self):
        self.ensure_auth()
        try:
            response = http_requests.get(f"{self.base_url}/v1/clinics", headers=self.get_headers())
            return response.json() if response.status_code == 200 else []
        except:
            return []

    def get_document_types(self):
        self.ensure_auth()
        try:
            response = http_requests.get(f"{self.base_url}/v1/documentTypes", headers=self.get_headers())
            return response.json() if response.status_code == 200 else []
        except:
            return []

    def get_webdoc_users(self):
        self.ensure_auth()
        try:
            response = http_requests.get(f"{self.base_url}/v1/users", headers=self.get_headers())
            return response.json() if response.status_code == 200 else []
        except:
            return []
            
    def get_patient(self, personal_number):
        self.ensure_auth()
        params = {"personalNumber": personal_number}
        clean_pn = personal_number.replace("-", "")
        try:
            response = http_requests.get(f"{self.base_url}/v2/patients", headers=self.get_headers(), params=params)
            if response.status_code == 200:
                patients = response.json()
                if patients and isinstance(patients, list):
                    for p in patients:
                        if p.get('personalNumber', '').replace("-", "") == clean_pn:
                            return p
                elif isinstance(patients, dict):
                    if patients.get('personalNumber', '').replace("-", "") == clean_pn:
                        return patients
            return None
        except:
            return None

    def upload_document(self, clinic_id, personal_number, filepath, document_type_id=1, user_id=None):
        if not self.access_token:
            return False, "Not authenticated"
            
        endpoint = f"{self.base_url}/v1/clinics/{clinic_id}/documents"
        path = Path(filepath)
        
        ext = path.suffix.lower()
        content_types = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.pdf': 'application/pdf',
            '.gif': 'image/gif', '.tif': 'image/tiff', '.tiff': 'image/tiff', '.bmp': 'image/bmp'
        }
        content_type = content_types.get(ext, 'application/octet-stream')
        
        try:
            with open(path, 'rb') as f:
                files = {'file': (path.name, f, content_type)}
                data = {
                    'documentTypeId': str(document_type_id),
                    'personalNumber': personal_number,
                    'createdAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                if user_id:
                    data['userId'] = user_id
                response = http_requests.post(endpoint, headers=self.get_headers(), files=files, data=data)
                
            if response.status_code in [200, 201, 202]:
                return True, "Uploaded"
            else:
                return False, response.text
        except Exception as e:
            return False, str(e)

    def update_patient_phone(self, personal_number, phone_number):
        self.ensure_auth()
        if not self.access_token:
            return False
            
        endpoint = f"{self.base_url}/v1/patients/{personal_number}"
        try:
            response = http_requests.patch(
                endpoint,
                headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
                json={"mobilePhoneNumber": phone_number}
            )
            return response.status_code in [200, 204]
        except Exception:
            return False

    def create_patient(self, personal_number, phone_number=None, patient_type="Vårdavtal Kardiologi"):
        """Create a new patient in Webdoc via SPAR integration."""
        self.ensure_auth()
        if not self.access_token:
            return False, "Not authenticated"
            
        endpoint = f"{self.base_url}/v1/patients"
        payload = {
            "personalNumber": personal_number,
            "patientType": patient_type
        }
        if phone_number:
            payload["mobileNumber"] = phone_number
            
        try:
            response = http_requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
                json=payload
            )
            if response.status_code in [200, 201, 204]:
                return True, response.json()
            else:
                return False, response.text
        except Exception as e:
            return False, str(e)

    def create_booking(self, personal_number, clinic_id, user_id, booking_type_id, date_str, time_str, end_time_str, note="Automated Booking", sms_confirmation=True, sms_reminder=False):
        """
        Creates a RemissIn booking in Webdoc to trigger the SMS confirmation,
        then immediately deletes it — the booking itself is not needed,
        only the SMS notification to the patient.
        """
        self.ensure_auth()
        if not self.access_token:
            return False, "Not authenticated"
            
        endpoint = f"{self.base_url}/v1/bookings"
        
        patient = self.get_patient(personal_number)
        if not patient or not patient.get('id'):
            return False, "Patient not found or could not retrieve UUID"
        
        patient_uuid = patient['id']
        
        payload = {
            "userId": user_id,
            "clinicId": clinic_id,
            "bookingTypeId": int(booking_type_id),
            "date": date_str,
            "startTime": time_str,
            "endTime": end_time_str,
            "patientId": patient_uuid,
            "allowOverlap": True,
            "note": note,
            "smsConfirmation": sms_confirmation,
            "smsReminder": sms_reminder
        }
        
        auth_headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
        
        try:
            # Step 1: Create booking (triggers SMS)
            response = http_requests.post(endpoint, headers=auth_headers, json=payload)
            if response.status_code not in [200, 201]:
                return False, response.text
            
            booking_data = response.json()
            booking_id = booking_data.get('id')
            
            # Step 2: Safety check — only delete if confirmed RemissIn booking type
            created_type = (booking_data.get('bookingType') or {}).get('name', '')
            if booking_id and created_type == 'RemissIn':
                del_resp = http_requests.delete(
                    f"{self.base_url}/v1/bookings/{booking_id}",
                    headers=auth_headers,
                    json={"userId": user_id}
                )
                if del_resp.status_code in [200, 204]:
                    return True, f"SMS triggered and RemissIn booking {booking_id} deleted"
                else:
                    # SMS was sent, cleanup failed — still a success
                    return True, f"SMS triggered but booking deletion failed ({del_resp.status_code}): {del_resp.text}"
            elif booking_id and created_type != 'RemissIn':
                # Safety guard: never delete non-RemissIn bookings
                print(f"[Warning] Unexpected booking type '{created_type}' — booking {booking_id} NOT deleted.")
                return True, f"SMS triggered but booking NOT deleted (type was '{created_type}', expected 'RemissIn')"
            
            return True, "SMS triggered (no booking ID returned)"
        except Exception as e:
            return False, str(e)



    def fetch_bookings(self, from_date, to_date):
        """Fetch all bookings in a date range with pagination."""
        self.ensure_auth()
        results = []
        offset = 0
        limit = 100
        
        while True:
            params = {
                "fromDate": from_date,
                "toDate": to_date,
                "offset": offset
            }
            try:
                response = http_requests.get(
                    f"{self.base_url}/v1/bookings",
                    headers=self.get_headers(),
                    params=params
                )
                if response.status_code == 200:
                    bookings = response.json()
                    results.extend(bookings)
                    if len(bookings) < limit:
                        break
                    offset += limit
                else:
                    break
            except:
                break
        
        return results

    def sync_bookings_to_db(self):
        """
        Sync bookings from Webdoc API to the local database.
        Only fetches new bookings since the last sync.
        Returns the number of new/updated patients.
        """
        self.ensure_auth()
        
        last_sync = db.get_last_sync_date("bookings")
        if last_sync is None:
            from_date = "2025-01-01"
        else:
            from_date = last_sync
        
        to_date = date.today().strftime("%Y-%m-%d")
        
        if from_date > to_date:
            return 0, "Already up to date"
        
        bookings = self.fetch_bookings(from_date, to_date)
        
        new_count = 0
        for b in bookings:
            patient = b.get('patient')
            if not patient:
                continue
            
            pn = patient.get('personalNumber')
            if not pn:
                continue
            
            booking_date = b.get('date', '')
            first_name = patient.get('firstName', '')
            last_name = patient.get('lastName', '')
            
            # Upsert patient — will only update first_booking_date if earlier
            db.upsert_patient(
                personal_number=pn,
                first_name=first_name,
                last_name=last_name,
                first_booking_date=booking_date
            )
            new_count += 1
        
        # Record sync
        db.set_last_sync_date("bookings", to_date)
        
        return new_count, f"Synced {len(bookings)} bookings, {new_count} patient records updated"


webdoc = WebdocClient()

# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('statistics'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('statistics'))
         
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = get_users()
        
        if username in users and users[username] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('statistics'))
        else:
            error = "Invalid username or password"
            
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', mode='errors')

@app.route('/dashboard/upload')
@login_required
def dashboard_upload():
    return render_template('dashboard.html', mode='upload')

@app.route('/statistics')
@login_required
def statistics():
    return render_template('statistics.html', mode='normal')

@app.route('/statistics/admin')
@login_required
def statistics_admin():
    return render_template('statistics.html', mode='admin')

@app.route('/statistics/incoming')
@login_required
def statistics_incoming():
    return render_template('statistics.html', mode='incoming')

@app.route('/guide')
@login_required
def guide():
    return render_template('guide.html')

# ---------------------------------------------------------
# API ROUTES
# ---------------------------------------------------------
@app.route('/api/status', methods=['GET'])
@login_required
def api_status():
    success, msg = webdoc.authenticate()
    return jsonify({"authenticated": success, "message": msg})

@app.route('/api/document_types', methods=['GET'])
@login_required
def api_document_types():
    webdoc.ensure_auth()
    types = webdoc.get_document_types()
    active_types = [t for t in types if t.get('active', True)]
    return jsonify(active_types)

@app.route('/api/clinics', methods=['GET'])
@login_required
def api_clinics():
    webdoc.ensure_auth()
    return jsonify(webdoc.get_clinics())

def extract_personnummer(filename):
    """Extract Swedish personnummer from filename."""
    name_without_ext = Path(filename).stem
    match = re.search(r'((?:19|20)\d{6})[-+]?(\d{4})[A-Za-z]?(?:\D|$)', name_without_ext)
    if match: return f"{match.group(1)}-{match.group(2)}"
    match = re.search(r'((?:19|20)\d{6})(\d{4})[A-Za-z]?(?:\D|$)', name_without_ext)
    if match: return f"{match.group(1)}-{match.group(2)}"
    match = re.search(r'(\d{6})[-+](\d{4})[A-Za-z]?(?:\D|$)', name_without_ext)
    if match: 
        century = "19" if int(match.group(1)[:2]) > 30 else "20"
        return f"{century}{match.group(1)}-{match.group(2)}"
    match = re.search(r'(\d{6})(\d{4})[A-Za-z]?(?:\D|$)', name_without_ext)
    if match:
        century = "19" if int(match.group(1)[:2]) > 30 else "20"
        return f"{century}{match.group(1)}-{match.group(2)}"
    return None

@app.route('/api/upload', methods=['POST'])
@login_required
def api_upload():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400

    clinic_id = request.form.get('clinicId')
    doc_type_id = request.form.get('documentTypeId')
    
    if not clinic_id or not doc_type_id:
        return jsonify({"success": False, "message": "Missing clinic ID or Document Type ID"}), 400
        
    extracted_pn = extract_personnummer(file.filename)
    
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    safe_filename = secure_filename(file.filename)
    temp_filepath = temp_dir / safe_filename
    file.save(temp_filepath)
    
    # OCR: Try to extract dates and PN from the document
    ocr_result = parse_document(str(temp_filepath))
    
    if not extracted_pn:
        extracted_pn = ocr_result.get('personnummer')
        
    if not extracted_pn:
        try:
            os.remove(temp_filepath)
        except:
            pass
        return jsonify({"success": False, "message": "Could not extract personnummer from filename or document text"}), 400
         
    webdoc.ensure_auth()
            
    patient = webdoc.get_patient(extracted_pn)
    if not patient:
        extracted_phone = ocr_result.get('phone_number')
        success, creation_res = webdoc.create_patient(extracted_pn, phone_number=extracted_phone)
        if not success:
            try:
                os.remove(temp_filepath)
            except:
                pass
            return jsonify({"success": False, "message": f"Patient with PN {extracted_pn} not found and creation failed: {creation_res}"}), 404
            
        # Refetch the patient to get the standardized name info
        patient = webdoc.get_patient(extracted_pn)
        if not patient:
            return jsonify({"success": False, "message": "Patient created successfully but could not be retrieved"}), 500
         
    # Find user ID
    target_user_id = None
    users = webdoc.get_webdoc_users()
    for u in users:
        u_name = f"{u.get('firstName', '')} {u.get('lastName', '')}".strip()
        if 'miltiadis' in u_name.lower() or 'miltiadis' in str(u.get('name', '')).lower():
            target_user_id = u.get('id')
            break
    
    # Upload to Webdoc
    success, msg = webdoc.upload_document(clinic_id, extracted_pn, str(temp_filepath), doc_type_id, user_id=target_user_id)
    
    try:
        os.remove(temp_filepath)
    except:
        pass
        
    if success:
        pn_formatted = patient.get('personalNumber', extracted_pn)
        name = f"{patient.get('firstName', '')} {patient.get('lastName', '')}".strip()
        
        # If we extracted a phone number and the patient doesn't have one in Webdoc, update it
        extracted_phone = ocr_result.get('phone_number')
        if extracted_phone and not patient.get('mobilePhoneNumber'):
            webdoc.update_patient_phone(pn_formatted, extracted_phone)

        from datetime import datetime, timedelta
        now = datetime.now()
        db.upsert_patient(
            personal_number=pn_formatted,
            first_name=patient.get('firstName', ''),
            last_name=patient.get('lastName', ''),
            phone_number=extracted_phone,
            referral_date=ocr_result.get('referral_date'),
            vardgaranti_date=ocr_result.get('vardgaranti_date'),
            uploaded_at=now.strftime('%Y-%m-%d')
        )
        
        # Create RemissIn booking
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M')
        end_dt = now + timedelta(minutes=15)
        end_time_str = end_dt.strftime('%H:%M')
        
        webdoc.create_booking(
            personal_number=pn_formatted,
            clinic_id=clinic_id,
            user_id=target_user_id,
            booking_type_id=29, # RemissIn
            date_str=date_str,
            time_str=time_str,
            end_time_str=end_time_str,
            note="Remiss uppladdad",
            sms_confirmation=True,
            sms_reminder=False
        )
        
        return jsonify({
            "success": True, 
            "message": "Uploaded successfully", 
            "patient": {"name": name, "pn": pn_formatted},
            "ocr": {
                "referral_date": ocr_result.get('referral_date'),
                "vardgaranti_date": ocr_result.get('vardgaranti_date'),
                "phone_number": ocr_result.get('phone_number'),
                "doc_type": ocr_result.get('doc_type'),
                "ocr_success": ocr_result.get('ocr_success', False)
            }
        })
    else:
        return jsonify({"success": False, "message": f"Upload failed: {msg}"}), 500



@app.route('/api/upload_group', methods=['POST'])
@login_required
def api_upload_group():
    uploaded_files = request.files.getlist('file')
    if not uploaded_files:
        return jsonify({"success": False, "message": "No files"}), 400
        
    clinic_id = request.form.get('clinicId')
    doc_type_id = request.form.get('documentTypeId')
    base_pn = request.form.get('basePersonnummer')
    
    if not clinic_id or not doc_type_id:
        return jsonify({"success": False, "message": "Missing clinic ID or Document Type ID"}), 400
        
    extracted_pn = extract_personnummer(base_pn) if base_pn else extract_personnummer(uploaded_files[0].filename)
    
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    
    # Save first file for OCR
    first_file = uploaded_files[0]
    safe_fn = secure_filename(first_file.filename)
    first_temp = temp_dir / safe_fn
    first_file.save(first_temp)
    
    ocr_result = parse_document(str(first_temp))
    
    if not extracted_pn:
        extracted_pn = ocr_result.get('personnummer')
        
    if not extracted_pn:
        try:
            os.remove(first_temp)
        except:
            pass
        return jsonify({"success": False, "message": "Could not extract personnummer from filename or document text"}), 400
         
    webdoc.ensure_auth()
            
    patient = webdoc.get_patient(extracted_pn)
    if not patient:
        success, creation_res = webdoc.create_patient(extracted_pn, phone_number=ocr_result.get('phone_number'))
        if not success:
            try:
                os.remove(first_temp)
            except:
                pass
            return jsonify({"success": False, "message": f"Patient with PN {extracted_pn} not found and creation failed: {creation_res}"}), 404
            
        # Refetch newly created patient
        patient = webdoc.get_patient(extracted_pn)
        if not patient:
            return jsonify({"success": False, "message": "Patient created successfully but could not be retrieved"}), 500
         
    target_user_id = None
    users = webdoc.get_webdoc_users()
    for u in users:
        u_name = f"{u.get('firstName', '')} {u.get('lastName', '')}".strip()
        if 'miltiadis' in u_name.lower() or 'miltiadis' in str(u.get('name', '')).lower():
            target_user_id = u.get('id')
            break

    # Find RemissBotPages doc_type_id 
    pages_doc_type_id = "21" # Default fallback
    for dt in webdoc.get_document_types():
        if dt.get('name', '').lower() == 'remissbotpages':
            pages_doc_type_id = str(dt.get('id'))
            break

    # Upload first document
    success, msg = webdoc.upload_document(clinic_id, extracted_pn, str(first_temp), doc_type_id, user_id=target_user_id)
    overall_success = success
    
    # Upload subsequent documents
    if len(uploaded_files) > 1:
        for file in uploaded_files[1:]:
            safe_fn = secure_filename(file.filename)
            temp_filepath = temp_dir / safe_fn
            file.save(temp_filepath)
            
            s, m = webdoc.upload_document(clinic_id, extracted_pn, str(temp_filepath), pages_doc_type_id, user_id=target_user_id)
            try:
                os.remove(temp_filepath)
            except:
                pass
                
            if not s:
                msg += f" | Failed to upload {safe_fn}: {m}"
                overall_success = False

    try:
        os.remove(first_temp)
    except:
        pass
        
    if overall_success:
        pn_formatted = patient.get('personalNumber', extracted_pn)
        name = f"{patient.get('firstName', '')} {patient.get('lastName', '')}".strip()
        
        extracted_phone = ocr_result.get('phone_number')
        if extracted_phone and not patient.get('mobilePhoneNumber'):
            webdoc.update_patient_phone(pn_formatted, extracted_phone)

        from datetime import datetime, timedelta
        now = datetime.now()
        db.upsert_patient(
            personal_number=pn_formatted,
            first_name=patient.get('firstName', ''),
            last_name=patient.get('lastName', ''),
            phone_number=extracted_phone,
            referral_date=ocr_result.get('referral_date'),
            vardgaranti_date=ocr_result.get('vardgaranti_date'),
            uploaded_at=now.strftime('%Y-%m-%d')
        )
        
        # Create RemissIn booking
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M')
        end_dt = now + timedelta(minutes=15)
        end_time_str = end_dt.strftime('%H:%M')
        
        webdoc.create_booking(
            personal_number=pn_formatted,
            clinic_id=clinic_id,
            user_id=target_user_id,
            booking_type_id=29, # RemissIn
            date_str=date_str,
            time_str=time_str,
            end_time_str=end_time_str,
            note="Remiss uppladdad (grupp)",
            sms_confirmation=True,
            sms_reminder=False
        )
        
        return jsonify({
            "success": True, 
            "message": "Uploaded group successfully", 
            "patient": {"name": name, "pn": pn_formatted},
            "ocr": {
                "referral_date": ocr_result.get('referral_date'),
                "vardgaranti_date": ocr_result.get('vardgaranti_date'),
                "phone_number": ocr_result.get('phone_number'),
                "doc_type": ocr_result.get('doc_type'),
                "ocr_success": ocr_result.get('ocr_success', False)
            }
        })
    else:
        return jsonify({"success": False, "message": f"Upload failed: {msg}"}), 500

# ---------------------------------------------------------
# STATISTICS & SYNC ROUTES
# ---------------------------------------------------------
@app.route('/api/sync_bookings', methods=['POST'])
@login_required
def api_sync_bookings():
    """Trigger a booking sync from Webdoc API to local DB."""
    try:
        count, msg = webdoc.sync_bookings_to_db()
        return jsonify({"success": True, "count": count, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
def filter_patients_by_date(patients, filter_type, start_date_str, end_date_str):
    if not start_date_str and not end_date_str:
        return patients
        
    filtered = []
    start_dt, end_dt = None, None
    if start_date_str:
        try: start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
        except: pass
    if end_date_str:
        try: end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
        except: pass
        
    for p in patients:
        val = p.get(filter_type)
        if not val: continue
        try:
            val_dt = datetime.strptime(val, '%Y-%m-%d')
            if start_dt and val_dt < start_dt: continue
            if end_dt and val_dt > end_dt: continue
            filtered.append(p)
        except:
            continue
            
    return filtered

@app.route('/api/patients', methods=['GET'])
@login_required
def api_patients():
    """Get all patients from the local database."""
    filter_type = request.args.get('filter_type', 'first_booking_date')
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    mode = request.args.get('mode', '')
    
    try:
        post_delay = int(request.args.get('post_delay', 0))
    except ValueError:
        post_delay = 0
        
    all_patients = db.get_all_patients()
    
    # Restrict incoming table noise: only show patients that hold any relevant referral date
    if mode == 'incoming':
        all_patients = [p for p in all_patients if p.get('uploaded_at') or p.get('referral_date') or p.get('vardgaranti_date')]
        
    patients = filter_patients_by_date(all_patients, filter_type, start_date, end_date)
    
    # Calculate waiting times
    today = datetime.now()
    for p in patients:
        p['wait_referral'] = None
        p['wait_vardgaranti'] = None
        
        if mode == 'incoming':
            # In incoming mode, calculate wait from today's date
            try:
                if p.get('referral_date'):
                    ref_dt = datetime.strptime(p['referral_date'], '%Y-%m-%d')
                    p['wait_referral'] = (today - ref_dt).days
                
                if p.get('vardgaranti_date'):
                    vg_dt = datetime.strptime(p['vardgaranti_date'], '%Y-%m-%d')
                    p['wait_vardgaranti'] = max(0, (today - vg_dt).days - post_delay)
            except (ValueError, TypeError):
                pass
        else:
            fbd = p.get('first_booking_date')
            if fbd:
                try:
                    booking_dt = datetime.strptime(fbd, '%Y-%m-%d')
                    
                    if p.get('referral_date'):
                        ref_dt = datetime.strptime(p['referral_date'], '%Y-%m-%d')
                        p['wait_referral'] = (booking_dt - ref_dt).days
                    
                    if p.get('vardgaranti_date'):
                        vg_dt = datetime.strptime(p['vardgaranti_date'], '%Y-%m-%d')
                        p['wait_vardgaranti'] = max(0, (booking_dt - vg_dt).days - post_delay)
                except (ValueError, TypeError):
                    pass
    
    return jsonify(patients)

@app.route('/api/patients/<personal_number>', methods=['PUT'])
@login_required
def api_update_patient(personal_number):
    """Update patient dates manually."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400
    
    referral_date = data.get('referral_date')
    vardgaranti_date = data.get('vardgaranti_date')
    
    # Validate date formats
    for d, label in [(referral_date, 'referral_date'), (vardgaranti_date, 'vardgaranti_date')]:
        if d and d != '':
            try:
                datetime.strptime(d, '%Y-%m-%d')
            except ValueError:
                return jsonify({"success": False, "message": f"Invalid date format for {label}. Use YYYY-MM-DD."}), 400
    
    db.update_patient_dates(personal_number, referral_date=referral_date, vardgaranti_date=vardgaranti_date)
    
    return jsonify({"success": True, "message": "Patient updated"})

@app.route('/api/patients/<personal_number>', methods=['DELETE'])
@login_required
def api_delete_patient(personal_number):
    """Delete a patient from the database."""
    db.delete_patient(personal_number)
    return jsonify({"success": True, "message": "Patient raderad"})

@app.route('/api/patients/<personal_number>/aterbesok', methods=['POST'])
@login_required
def api_toggle_aterbesok(personal_number):
    """Toggle the Återbesök flag for a patient."""
    new_val = db.toggle_aterbesok(personal_number)
    if new_val is None:
        return jsonify({"success": False, "message": "Patient hittades inte"}), 404
    return jsonify({"success": True, "is_aterbesok": new_val, "message": "Markerad som Återbesök" if new_val else "Återbesök borttagen"})

# ---------------------------------------------------------
# BOT ERROR MANAGEMENT API
# ---------------------------------------------------------
BOT_WATCH_DIR = Path(r"\\HJ-VAR-DT01\Pictures\2026Scan\Bot")
BOT_ERROR_DIR = BOT_WATCH_DIR / "Error"

def _sync_error_folder_to_db():
    """Scan Error folder for files not tracked in DB and auto-import them."""
    try:
        if not BOT_ERROR_DIR.exists():
            return
        
        # Get all files in Error folder
        error_files = [f for f in BOT_ERROR_DIR.iterdir() if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.pdf']]
        if not error_files:
            return
        
        # Group by personnummer (filename format: YYYYMMDD-XXXX_N.ext)
        from collections import defaultdict
        groups = defaultdict(list)
        for f in error_files:
            pn = extract_personnummer(f.name)
            if pn:
                groups[pn].append(f.name)
            else:
                groups['OKÄNT'].append(f.name)
        
        # Check which PNs are already tracked as unresolved errors in DB
        existing_errors = db.get_bot_errors(resolved=False)
        tracked_files = set()
        for err in existing_errors:
            for fname in err['file_names']:
                tracked_files.add(fname)
        
        # Import untracked groups
        for pn, files in groups.items():
            # Check if any of these files are already tracked
            untracked = [f for f in files if f not in tracked_files]
            if untracked:
                db.log_bot_error(
                    personal_number=pn,
                    file_names=untracked,
                    error_message='Hittad i Error-mappen (äldre fel, orsak okänd)',
                    error_type='upload'
                )
    except Exception as e:
        print(f"Error syncing error folder: {e}")

@app.route('/api/bot_errors', methods=['GET'])
@login_required
def api_bot_errors():
    """Get all unresolved bot errors. Auto-imports orphaned Error folder files."""
    _sync_error_folder_to_db()
    errors = db.get_bot_errors(resolved=False)
    return jsonify(errors)

@app.route('/api/bot_errors/count', methods=['GET'])
@login_required
def api_bot_errors_count():
    """Get count of unresolved bot errors (for nav badge)."""
    count = db.get_bot_error_count()
    # Also count files currently in Error folder
    folder_count = 0
    try:
        if BOT_ERROR_DIR.exists():
            folder_count = len([f for f in BOT_ERROR_DIR.iterdir() if f.is_file()])
    except:
        pass
    return jsonify({"db_errors": count, "folder_files": folder_count})

@app.route('/api/bot_errors/<int:error_id>/reprocess', methods=['POST'])
@login_required
def api_reprocess_error(error_id):
    """Move error files back to a PN-named subfolder in watch directory for reprocessing."""
    error = db.get_bot_error(error_id)
    if not error:
        return jsonify({"success": False, "message": "Fel hittades inte"}), 404
    
    # Create a subfolder named by PN so the bot picks it up as a group
    pn = error.get('personal_number', 'UNKNOWN')
    reprocess_dir = BOT_WATCH_DIR / f"reprocess_{pn}"
    reprocess_dir.mkdir(parents=True, exist_ok=True)
    
    moved = 0
    not_found = 0
    for fname in error['file_names']:
        src = BOT_ERROR_DIR / fname
        if src.exists():
            dst = reprocess_dir / fname
            try:
                shutil.move(str(src), str(dst))
                moved += 1
            except Exception as e:
                return jsonify({"success": False, "message": f"Kunde inte flytta {fname}: {e}"}), 500
        else:
            not_found += 1
    
    db.resolve_bot_error(error_id)
    msg = f"{moved} fil(er) flyttade till {reprocess_dir.name}/ för ombearbetning"
    if not_found:
        msg += f" ({not_found} hittades inte i Error-mappen)"
    return jsonify({"success": True, "message": msg})

@app.route('/api/bot_errors/<int:error_id>/resolve', methods=['POST'])
@login_required
def api_resolve_error(error_id):
    """Mark error as resolved without reprocessing."""
    error = db.get_bot_error(error_id)
    if not error:
        return jsonify({"success": False, "message": "Fel hittades inte"}), 404
    
    # Optionally clean up Error folder files
    for fname in error['file_names']:
        src = BOT_ERROR_DIR / fname
        if src.exists():
            try:
                os.remove(str(src))
            except:
                pass
    
    db.resolve_bot_error(error_id)
    return jsonify({"success": True, "message": "Markerad som löst"})

@app.route('/api/bot_errors/<int:error_id>', methods=['DELETE'])
@login_required
def api_delete_error(error_id):
    """Delete an error record."""
    error = db.get_bot_error(error_id)
    if not error:
        return jsonify({"success": False, "message": "Fel hittades inte"}), 404
    db.delete_bot_error(error_id)
    return jsonify({"success": True, "message": "Felpost raderad"})

@app.route('/api/statistics/summary', methods=['GET'])
@login_required
def api_statistics_summary():
    """Get aggregate statistics (mean/median waiting times)."""
    filter_type = request.args.get('filter_type', 'first_booking_date')
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    mode = request.args.get('mode', '')
    
    try:
        post_delay = int(request.args.get('post_delay', 0))
    except ValueError:
        post_delay = 0
        
    all_patients = db.get_all_patients()
    
    if mode == 'incoming':
        all_patients = [p for p in all_patients if p.get('uploaded_at') or p.get('referral_date') or p.get('vardgaranti_date')]
    
    # Exclude Återbesök patients from calculations
    all_patients = [p for p in all_patients if not p.get('is_aterbesok')]
        
    patients = filter_patients_by_date(all_patients, filter_type, start_date, end_date)
    
    wait_referral_list = []
    wait_vardgaranti_list = []
    delay_extern_list = []
    
    for p in patients:
        fbd = p.get('first_booking_date')
        if fbd:
            try:
                booking_dt = datetime.strptime(fbd, '%Y-%m-%d')
                
                if p.get('referral_date'):
                    ref_dt = datetime.strptime(p['referral_date'], '%Y-%m-%d')
                    wait_referral_list.append((booking_dt - ref_dt).days)
                
                if p.get('vardgaranti_date'):
                    vg_dt = datetime.strptime(p['vardgaranti_date'], '%Y-%m-%d')
                    wait_vardgaranti_list.append(max(0, (booking_dt - vg_dt).days - post_delay))
                    
                if p.get('referral_date') and p.get('vardgaranti_date'):
                    # Add Postledtid structurally as requested by user
                    delay_extern_list.append((vg_dt - ref_dt).days + post_delay)
            except (ValueError, TypeError):
                pass
    
    def calc_stats(values):
        if not values:
            return {"mean": None, "median": None, "count": 0, "under_60_pct": None, "under_90_pct": None}
        values_sorted = sorted(values)
        n = len(values_sorted)
        mean_val = sum(values_sorted) / n
        if n % 2 == 0:
            median_val = (values_sorted[n // 2 - 1] + values_sorted[n // 2]) / 2
        else:
            median_val = values_sorted[n // 2]
            
        under_60 = sum(1 for v in values_sorted if v <= 60)
        under_90 = sum(1 for v in values_sorted if v <= 90)
        
        pct_60 = round((under_60 / n) * 100, 1)
        pct_90 = round((under_90 / n) * 100, 1)
        
        return {
            "mean": round(mean_val, 1), 
            "median": round(median_val, 1), 
            "count": n,
            "under_60_pct": pct_60,
            "under_90_pct": pct_90
        }
    
    return jsonify({
        "total_patients": len(patients),
        "referral_stats": calc_stats(wait_referral_list),
        "vardgaranti_stats": calc_stats(wait_vardgaranti_list),
        "extern_stats": calc_stats(delay_extern_list),
        "last_sync": db.get_last_sync_date("bookings")
    })

@app.route('/api/statistics/trend', methods=['GET'])
@login_required
def api_statistics_trend():
    """Get month-by-month compliance percentages for trend graphs."""
    filter_type = request.args.get('filter_type', 'first_booking_date')
    
    try:
        post_delay = int(request.args.get('post_delay', 0))
    except ValueError:
        post_delay = 0
        
    all_patients = db.get_all_patients()
    # Exclude Återbesök patients from trend calculations
    all_patients = [p for p in all_patients if not p.get('is_aterbesok')]
    
    # We will group by the filter_type (month-year)
    from collections import defaultdict
    months = defaultdict(lambda: {"ref": [], "vg": [], "ext": []})
    
    for p in all_patients:
        dt_str = p.get(filter_type)
        if not dt_str: continue
        
        try:
            val_dt = datetime.strptime(dt_str, '%Y-%m-%d')
            month_key = val_dt.strftime('%G-W%V') # e.g. '2026-W05' for ISO Week
        except:
            continue
            
        # Calculate actual waits
        fbd = p.get('first_booking_date')
        if not fbd: continue
        try:
            booking_dt = datetime.strptime(fbd, '%Y-%m-%d')
            if p.get('referral_date'):
                ref_dt = datetime.strptime(p['referral_date'], '%Y-%m-%d')
                months[month_key]["ref"].append((booking_dt - ref_dt).days)
                
            if p.get('vardgaranti_date'):
                vg_dt = datetime.strptime(p['vardgaranti_date'], '%Y-%m-%d')
                months[month_key]["vg"].append(max(0, (booking_dt - vg_dt).days - post_delay))
                
            if p.get('referral_date') and p.get('vardgaranti_date'):
                months[month_key]["ext"].append((vg_dt - ref_dt).days + post_delay)
        except:
            pass
            
    # Calculate percentages per month
    trend_data = []
    
    for mk in sorted(months.keys()):
        data = months[mk]
        
        # Helper inline
        def pct(lst, threshold):
            if not lst: return None
            return round((sum(1 for v in lst if v <= threshold) / len(lst)) * 100, 1)

        # Helper inline for averages
        def mean(lst):
            if not lst: return None
            return round(sum(lst) / len(lst), 1)

        trend_data.append({
            "month": mk,
            "ref_count": len(data["ref"]),
            "vg_count": len(data["vg"]),
            "ext_count": len(data["ext"]),
            "ref_under_60": pct(data["ref"], 60),
            "ref_under_90": pct(data["ref"], 90),
            "vg_under_60": pct(data["vg"], 60),
            "vg_under_90": pct(data["vg"], 90),
            "ext_mean": mean(data["ext"])
        })


    return jsonify(trend_data)

@app.route('/api/statistics/incoming_data', methods=['GET'])
@login_required
def api_statistics_incoming_data():
    filter_type = request.args.get('filter_type', 'vardgaranti_date')
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    
    all_patients = db.get_all_patients()
    # Filter incoming base set: require at least one referral date
    all_patients = [p for p in all_patients if p.get('uploaded_at') or p.get('referral_date') or p.get('vardgaranti_date')]
    # Exclude Återbesök patients from incoming calculations
    all_patients = [p for p in all_patients if not p.get('is_aterbesok')]
    
    patients = filter_patients_by_date(all_patients, filter_type, start_date, end_date)
    
    from collections import defaultdict
    # Map weeks falling back to other dates if Vårdgaranti is missing
    incoming_weeks = defaultdict(lambda: {"booked": 0, "unbooked": 0})
    
    for p in patients:
        base_date_str = p.get('vardgaranti_date') or p.get('referral_date') or p.get('uploaded_at')
        if not base_date_str: 
            continue
            
        try:
            d_str = base_date_str.split(' ')[0]
            vg_dt = datetime.strptime(d_str, '%Y-%m-%d')
            week_key = vg_dt.strftime('%G-W%V')
            
            if p.get('first_booking_date'):
                incoming_weeks[week_key]["booked"] += 1
            else:
                incoming_weeks[week_key]["unbooked"] += 1
        except:
            pass
            
    # Sort chronologically by Week ISO format
    sorted_weeks = sorted(incoming_weeks.keys())
    
    volume_data = []
    total_booked = 0
    total_unbooked = 0
    
    for wk in sorted_weeks:
        b = incoming_weeks[wk]["booked"]
        u = incoming_weeks[wk]["unbooked"]
        total_booked += b
        total_unbooked += u
        
        volume_data.append({
            "week": wk,
            "booked_count": b,
            "unbooked_count": u,
            "total_count": b + u
        })
        
    from statistics import mean
    
    is_filtered_timeline = bool(start_date or end_date)
    valid_median_weeks = []
    
    # Calculate median using only the last 2 weeks if no specific date filter is active
    recent_volume = volume_data if is_filtered_timeline else volume_data[-2:]
    
    for d in recent_volume:
        # If dates are explicitly defined, ALL weeks apply. If full timeline, only weeks > 10 apply to strip dead weeks.
        if is_filtered_timeline:
            valid_median_weeks.append(d["total_count"])
        else:
            if d["total_count"] > 10:
                valid_median_weeks.append(d["total_count"])
                
    # Using 'mean' mathematically matches the user's explicit definition of 'devide with week count'
    median_per_week = round(mean(valid_median_weeks), 1) if valid_median_weeks else 0
        
    return jsonify({
        "total_incoming": total_booked + total_unbooked,
        "total_booked": total_booked,
        "total_unbooked": total_unbooked,
        "median_per_week": median_per_week,
        "chart_data": volume_data,
        "last_sync": db.get_last_sync_date("bookings")
    })

@app.route('/api/export_statistics', methods=['GET'])
@login_required
def api_export_statistics():
    """Export statistics as CSV."""
    import csv
    import io
    
    filter_type = request.args.get('filter_type', 'first_booking_date')
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    
    try:
        post_delay = int(request.args.get('post_delay', 0))
    except ValueError:
        post_delay = 0
        
    all_patients = db.get_all_patients()
    patients = filter_patients_by_date(all_patients, filter_type, start_date, end_date)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Instruction headers for manual Excel editing
    writer.writerow(['OBS! Instruktioner för manuell ifyllnad i Excel:'])
    writer.writerow(['Ändra ENDAST kolumnerna "Remissdatum" och "Vårdgarantidatum". "Första Bokning" synkas via Webdoc.'])
    writer.writerow(['ANVÄND ENDAST FORMATET YYYY-MM-DD (T.ex: 2026-05-30). Andra format ignoreras vid import!'])
    writer.writerow([]) # Empty spacer row
    
    writer.writerow([
        'Personnummer', 'Förnamn', 'Efternamn', 
        'Uppladdningsdatum', 'Remissdatum', 'Vårdgarantidatum', 'Första Bokning',
        'Väntetid Remiss (dagar)', 'Väntetid Vårdgaranti (dagar)'
    ])
    
    for p in patients:
        wait_ref = ''
        wait_vg = ''
        fbd = p.get('first_booking_date', '')
        
        if fbd:
            try:
                booking_dt = datetime.strptime(fbd, '%Y-%m-%d')
                if p.get('referral_date'):
                    wait_ref = (booking_dt - datetime.strptime(p['referral_date'], '%Y-%m-%d')).days
                if p.get('vardgaranti_date'):
                    wait_vg = max(0, (booking_dt - datetime.strptime(p['vardgaranti_date'], '%Y-%m-%d')).days - post_delay)
            except:
                pass
        
        writer.writerow([
            p.get('personal_number', ''),
            p.get('first_name', ''),
            p.get('last_name', ''),
            p.get('uploaded_at', ''),
            p.get('referral_date', ''),
            p.get('vardgaranti_date', ''),
            fbd,
            wait_ref,
            wait_vg
        ])
    
    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv; charset=utf-8-sig',
        'Content-Disposition': f'attachment; filename=statistik_{timestamp}.csv'
    }


@app.route('/api/import_statistics', methods=['POST'])
@login_required
def api_import_statistics():
    """Import CSV to manually correct referral and vardgaranti dates."""
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected"}), 400
        
    import csv
    import io
    
    try:
        raw_bytes = file.stream.read()
        try:
            decoded_text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                decoded_text = raw_bytes.decode("cp1252")
            except UnicodeDecodeError:
                decoded_text = raw_bytes.decode("iso-8859-1", errors="replace")
                
        stream = io.StringIO(decoded_text, newline=None)
        
        # Sniff delimiter because Swedish Excel saves CSVs with semicolons
        dialect = csv.excel
        try:
            sample = stream.read(1024)
            stream.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=[',', ';', '\t'])
        except Exception:
            dialect = csv.excel
            
        reader = csv.reader(stream, dialect=dialect)
        rows = list(reader)
        
        # Find the actual header row (look for 'Personnummer')
        header_idx = -1
        for i, row in enumerate(rows):
            if row and len(row) > 0 and 'Personnummer' in row[0]:
                header_idx = i
                break
                
        if header_idx == -1:
            return jsonify({"success": False, "message": "Kunde inte hitta 'Personnummer' kolumnen. Är detta rätt fil?"}), 400
            
        headers = rows[header_idx]
        try:
            pn_idx = headers.index('Personnummer')
            rec_idx = headers.index('Remissdatum')
            vg_idx = headers.index('Vårdgarantidatum')
        except ValueError:
            return jsonify({"success": False, "message": "Saknar nödvändiga kolumner i CSV-filen."}), 400
            
        updated_count = 0
        def parse_date(date_str):
            if not date_str or not str(date_str).strip():
                return ""
            
            d_str = str(date_str).strip()
            # Try exact standard format first YYYY-MM-DD
            try:
                datetime.strptime(d_str, '%Y-%m-%d')
                return d_str
            except ValueError:
                pass
                
            # Attempt Excel corrupted auto-fixes (DD/MM/YYYY, MM/DD/YYYY, etc)
            for fmt in ('%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y'):
                try:
                    return datetime.strptime(d_str, fmt).strftime('%Y-%m-%d')
                except ValueError:
                    pass
            return None # Invalid Date
        
        for row in rows[header_idx+1:]:
            if len(row) <= max(pn_idx, rec_idx, vg_idx):
                continue
                
            pn = str(row[pn_idx]).strip()
            if not pn:
                continue
                
            rec_raw = row[rec_idx]
            vg_raw = row[vg_idx]
            
            rec_clean = parse_date(rec_raw)
            vg_clean = parse_date(vg_raw)
            
            # If a strict parse failure happens and the string isn't empty, warn but skip that row
            if rec_clean is None or vg_clean is None:
                continue
                
            db.update_patient_dates(pn, referral_date=rec_clean if rec_clean else None, vardgaranti_date=vg_clean if vg_clean else None)
            updated_count += 1
            
        return jsonify({"success": True, "message": f"{updated_count} patienter uppdaterades från Excel-filen!"})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Filfel: {str(e)}"}), 500

if __name__ == '__main__':
    Path("templates").mkdir(exist_ok=True)
    Path("static").mkdir(exist_ok=True)
    app.run(host='0.0.0.0', port=5000)
