import os
import time
import shutil
from pathlib import Path
from PIL import Image
import img2pdf
from io import BytesIO

# Fix directory to ensure we run cleanly relative to WebdocAPI
import sys
project_root = str(Path(__file__).parent.absolute())
sys.path.insert(0, project_root)

import doc_parser
# Import from our existing app seamlessly
from app import webdoc, db, app as flask_app, extract_personnummer

WATCH_DIR = Path(r"\\HJ-VAR-DT01\Pictures\2026Scan\Bot")
PROCESSED_DIR = WATCH_DIR / "Processed"
ERROR_DIR = WATCH_DIR / "Error"

# Throttle delay between patients to avoid API rate limiting
PATIENT_DELAY_SECONDS = 5

def setup_dirs():
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ERROR_DIR.mkdir(parents=True, exist_ok=True)

def process_single_group(pn, files, is_folder=False):
    """
    Processes a group of files belonging to one patient PN.
    Merges them into ONE PDF, then uploads to Webdoc as RemissBot (20).
    """
    if not files: return False, "No files"
    
    # 1. Provide Context & Extract all intelligence across ALL pages
    best_phone = None
    best_ref_date = None
    best_vg_date = None
    
    for f in files:
        res = doc_parser.parse_document(str(f))
        if res.get('phone_number') and not best_phone: best_phone = res.get('phone_number')
        if res.get('referral_date') and not best_ref_date: best_ref_date = res.get('referral_date')
        if res.get('vardgaranti_date') and not best_vg_date: best_vg_date = res.get('vardgaranti_date')

    print(f"[{pn}] Extracted -> Phone: {best_phone}, RefDate: {best_ref_date}, VGDate: {best_vg_date}")
    
    # 2. Authenticate
    webdoc.ensure_auth()
    
    # 3. Patient logic
    patient = webdoc.get_patient(pn)
    if not patient:
        print(f"[{pn}] Patient missing. Auto-creating...")
        success, creation_res = webdoc.create_patient(pn, phone_number=best_phone)
        if not success:
            print(f"[{pn}] Creation failed! {creation_res}")
            return False, f"Failed to create patient: {creation_res}"
        patient = webdoc.get_patient(pn)
        if not patient:
            return False, "Failed to refetch created patient"
            
    # 4. Update missing phone if extracted
    pn_formatted = patient.get('personalNumber', pn)
    if best_phone and not patient.get('mobilePhoneNumber'):
        webdoc.update_patient_phone(pn_formatted, best_phone)
        
    # 5. Get system IDs
    clinics = webdoc.get_clinics()
    if not clinics: return False, "No clinics configured"
    clinic_id = clinics[0]['id']
    
    target_user_id = None
    users = webdoc.get_webdoc_users()
    for u in users:
        name = str(u.get('name', '')).lower() + " " + u.get('firstName', '').lower()
        if 'miltiadis' in name:
            target_user_id = u.get('id')
            break
            
    # Get RemissBot doc type (20)
    doc_type_id = "20"
    for dt in webdoc.get_document_types():
        if dt.get('name', '').lower() == 'remissbot':
            doc_type_id = str(dt.get('id'))
            break
            
    # 6. Merge to PDF
    image_bytes_list = []
    has_errors = False
    for f in files:
        try:
            img = Image.open(f)
            if img.mode != 'RGB': img = img.convert('RGB')
            buf = BytesIO()
            img.save(buf, format='JPEG', quality=85)
            image_bytes_list.append(buf.getvalue())
            img.close()
        except Exception as e:
            print(f"[{pn}] Error parsing image {f}: {e}")
            has_errors = True
            
    if not image_bytes_list:
        return False, "No valid images to compile"
        
    temp_pdf = WATCH_DIR / f"{pn}_merged.pdf"
    try:
        pdf_bytes = img2pdf.convert(image_bytes_list)
        with open(temp_pdf, "wb") as f_out:
            f_out.write(pdf_bytes)
            
        print(f"[{pn}] Uploading {len(files)} pages as PDF to Webdoc...")
        success, msg = webdoc.upload_document(clinic_id, pn_formatted, str(temp_pdf), doc_type_id, user_id=target_user_id)
        
        try: os.remove(temp_pdf)
        except: pass
        
        if success:
            # Upload succeeded — from here on, errors are non-critical
            # Wrap post-upload steps so they can't cause files to go to Error
            
            try:
                from datetime import datetime, timedelta
                now = datetime.now()
                db.upsert_patient(
                    personal_number=pn_formatted,
                    first_name=patient.get('firstName', ''),
                    last_name=patient.get('lastName', ''),
                    phone_number=best_phone,
                    referral_date=best_ref_date,
                    vardgaranti_date=best_vg_date,
                    uploaded_at=now.strftime('%Y-%m-%d')
                )
                print(f"[{pn}] Upload complete and DB synced!")
            except Exception as e:
                print(f"[{pn}] WARNING: DB sync failed (upload OK): {e}")
            
            try:
                from datetime import datetime, timedelta
                now = datetime.now()
                # Create RemissIn booking
                date_str = now.strftime('%Y-%m-%d')
                time_str = now.strftime('%H:%M')
                end_dt = now + timedelta(minutes=15)
                end_time_str = end_dt.strftime('%H:%M')
                
                b_success, b_msg = webdoc.create_booking(
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
                if b_success:
                    print(f"[{pn}] RemissIn booking created successfully.")
                else:
                    print(f"[{pn}] Failed to create RemissIn booking: {b_msg}")
            except Exception as e:
                print(f"[{pn}] WARNING: Booking creation failed (upload OK): {e}")
                
            return True, "Uploaded perfectly"
        else:
            print(f"[{pn}] Webdoc upload failed: {msg}")
            return False, f"Upload API failed: {msg}"
            
    except Exception as e:
        try: os.remove(temp_pdf)
        except: pass
        return False, f"PDF compilation error: {e}"

def process_queue():
    # Global collector for this exact run
    global_groups = {}
    
    def process_chronological_batch(jpgs):
        if not jpgs:
            return
            
        # Ensure chronological ordering to match physical scanner stack
        jpgs.sort(key=lambda x: x.name)
        current_pn = None
        
        for f in jpgs:
            base_pn = extract_personnummer(f.name)
            
            if not base_pn:
                print(f"Running OCR on file: {f.name}...")
                res = doc_parser.parse_document(str(f))
                base_pn = res.get('personnummer')
                
            if base_pn:
                current_pn = base_pn
                
            if not current_pn:
                # No current PN and OCR failed -> orphaned top-of-stack page
                print(f"FAILED to find PN for {f.name} and no active patient! Moving to Error.")
                tgt = ERROR_DIR / f.name
                if tgt.exists(): os.remove(tgt)
                try: shutil.move(str(f), str(tgt))
                except: pass
                # Log orphaned file error
                try:
                    db.log_bot_error(
                        personal_number="OKÄNT",
                        file_names=[f.name],
                        error_message="Kunde inte extrahera personnummer från filnamn eller OCR",
                        error_type="ocr"
                    )
                except: pass
                continue
                
            if current_pn not in global_groups:
                global_groups[current_pn] = []
                
            # Rename the actual JPG file to standard convention
            idx = len(global_groups[current_pn]) + 1
            new_name = f"{current_pn}_{idx}{f.suffix}"
            new_path = f.parent / new_name
            
            if f.name != new_name and not new_path.exists():
                try:
                    f.rename(new_path)
                    f = new_path
                except:
                    pass
            elif new_path.exists() and f.name != new_name:
                 new_name = f"{current_pn}_{int(time.time())}_{idx}{f.suffix}"
                 new_path = f.parent / new_name
                 try: f.rename(new_path); f = new_path
                 except: pass

            global_groups[current_pn].append(f)

    # 1. Gather all subfolders and process as independent chronological stacks
    for item in WATCH_DIR.iterdir():
        if item.is_dir() and item.name not in ['Processed', 'Error']:
            sub_jpgs = [f for f in item.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg']]
            process_chronological_batch(sub_jpgs)
            
    # 2. Gather all loose files as one chronological stack
    loose_jpgs = [f for f in WATCH_DIR.iterdir() if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg']]
    process_chronological_batch(loose_jpgs)
    
    # 3. Commit EVERYTHING merged together — with throttle delay between patients
    patient_count = 0
    for pn, files in global_groups.items():
        # Throttle: wait between patients to avoid API rate limiting
        if patient_count > 0:
            print(f"Throttle: waiting {PATIENT_DELAY_SECONDS}s before next patient...")
            time.sleep(PATIENT_DELAY_SECONDS)
        
        patient_count += 1
        print(f"Commit ALL combined groups for {pn} ({len(files)} total pages)")
        success, err = process_single_group(pn, files)
        if success:
            for f in files:
                tgt = PROCESSED_DIR / f.name
                if tgt.exists(): os.remove(tgt)
                try: shutil.move(str(f), str(tgt))
                except: pass
        else:
            # Log the error to DB for UI visibility
            try:
                file_names = [f.name for f in files]
                db.log_bot_error(
                    personal_number=pn,
                    file_names=file_names,
                    error_message=err,
                    error_type='upload'
                )
            except Exception as log_err:
                print(f"[{pn}] Could not log error to DB: {log_err}")
            
            for f in files:
                tgt = ERROR_DIR / f.name
                if tgt.exists(): os.remove(tgt)
                try: shutil.move(str(f), str(tgt))
                except: pass
                
    # 4. Clean up empty subdirectories
    for item in WATCH_DIR.iterdir():
        if item.is_dir() and item.name not in ['Processed', 'Error']:
            if not list(item.iterdir()):
                try: item.rmdir()
                except: pass

if __name__ == '__main__':
    setup_dirs()
    print(f"Watcher Bot Started on {WATCH_DIR}...")
    while True:
        try:
            process_queue()
        except Exception as e:
            print("CRASH AVOIDED in main loop:", e)
        time.sleep(10)
