"""
Webdoc Statistics Extraction Pipeline (Statistikuttag)

Extacts bookings filtered by date range, fetches inreferral dates, patient types, payments,
freeCard validities, and visits, then exports to a pandas DataFrame and CSV/Excel.
"""

import argparse
import sys
import os
import re
from datetime import datetime
import requests
import pandas as pd
from pathlib import Path

class WebdocStatisticsExtractor:
    def __init__(self, prod_env=True):
        self.prod_env = prod_env
        self.setup_credentials()
        self.access_token = None
        
        # In-memory dictionaries
        self.clinics = []
        self.patient_types_dict = {}
        self.action_codes_dict = {}
        
    def setup_credentials(self):
        """Load credentials based on environment."""
        if self.prod_env:
            self.auth_url = "https://auth.atlan.se"
            self.base_url = "https://api.atlan.se"
            
            # Try loading from api.txt for production
            try:
                with open('api.txt', 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.client_id = re.search(r'ClientID:\s*(.+)', content).group(1).strip()
                    self.client_secret = re.search(r'Secret:\s*(.+)', content).group(1).strip()
                    print("Loaded Production credentials from api.txt")
            except Exception as e:
                print(f"Failed to load api.txt: {e}")
                self.client_id = "YOUR_CLIENT_ID"
                self.client_secret = "YOUR_CLIENT_SECRET"  # Fallback
        else:
            self.auth_url = "https://auth-integration.carasent.net"
            self.base_url = "https://api-integration.carasent.net"
            self.client_id = "YOUR_CLIENT_ID"
            self.client_secret = "YOUR_CLIENT_SECRET"
            print("Loaded Integration credentials")

    def authenticate(self):
        """Authenticate with Webdoc OAuth2 endpoint."""
        token_endpoint = f"{self.auth_url}/oauth/token"
        
        # Scopes requested in implementation plan
        scopes = "documents:write patient:read document-types:read clinics:read users:read bookings:read patient-types:read actioncodes:read"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": scopes
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        print("\nAuthenticating...")
        try:
            response = requests.post(token_endpoint, data=data, headers=headers)
            if response.status_code == 200:
                self.access_token = response.json().get("access_token")
                print("✓ Authentication successful!")
                return True
            else:
                print(f"✗ Authentication failed: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Authentication error: {e}")
            return False

    def get_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    def fetch_base_dictionaries(self):
        """Fetch clinics, patient types, and action codes."""
        print("\nFetching Base Data Dictionaries...")
        headers = self.get_headers()
        
        # 1. Get Clinics
        res_clinics = requests.get(f"{self.base_url}/v1/clinics", headers=headers)
        if res_clinics.status_code == 200:
            self.clinics = res_clinics.json()
            print(f"  ✓ Fetched {len(self.clinics)} Clinics")
        
        # 2. Get Patient Types
        res_ptypes = requests.get(f"{self.base_url}/v1/patientTypes", headers=headers)
        if res_ptypes.status_code == 200:
            types = res_ptypes.json()
            self.patient_types_dict = {str(t.get('id')): t for t in types}
            print(f"  ✓ Fetched {len(types)} Patient Types")
            
        # 3. Get Action Codes
        res_acodes = requests.get(f"{self.base_url}/v1/actionCodes", headers=headers)
        if res_acodes.status_code == 200:
            codes = res_acodes.json()
            self.action_codes_dict = {str(c.get('id')): c for c in codes}
            print(f"  ✓ Fetched {len(codes)} Action Codes")
            
    def fetch_bookings(self, start_date, end_date):
        """Fetch all bookings within date range using pagination."""
        print(f"\nFetching Bookings from {start_date} to {end_date}...")
        results = []
        
        endpoint = f"{self.base_url}/v1/bookings"
        base_params = {
            "fromDate": start_date,
            "toDate": end_date
        }
        
        offset = 0
        limit = 100
        while True:
            params = base_params.copy()
            params["offset"] = offset
            
            response = requests.get(endpoint, headers=self.get_headers(), params=params)
            
            if response.status_code == 200:
                bookings = response.json()
                results.extend(bookings)
                print(f"  ✓ Fetched batch of {len(bookings)} bookings (Total: {len(results)})...")
                
                if len(bookings) < limit:
                    break
                offset += limit
            elif response.status_code in [404, 403, 400] and self.clinics and not results:
                # Fallback to clinic specific bookings if global fails on first try
                for clinic in self.clinics:
                    c_id = clinic['id']
                    c_offset = 0
                    print(f"  Fallback: Fetching bookings for clinic {c_id}")
                    while True:
                        c_params = base_params.copy()
                        c_params["offset"] = c_offset
                        res = requests.get(f"{self.base_url}/v1/clinics/{c_id}/bookings", 
                                           headers=self.get_headers(), params=c_params)
                        if res.status_code == 200:
                            c_bookings = res.json()
                            results.extend(c_bookings)
                            print(f"    ✓ Fetched batch of {len(c_bookings)} bookings (Total so far: {len(results)})...")
                            if len(c_bookings) < limit:
                                break
                            c_offset += limit
                        else:
                            break
                break
            else:
                print(f"  ✗ Failed to fetch bookings: {response.text}")
                break
            
        print(f"  ✓ Retrieved {len(results)} total bookings")
        return results

    def fetch_patient_first_booking_date(self, personal_number):
        """Fetch the earliest booking date for a patient as surrogate for inreferral/registration date."""
        if not personal_number:
            return None
            
        endpoint = f"{self.base_url}/v1/bookings"
        params = {
            "personalNumber": personal_number,
            "fromDate": "2000-01-01",
            "toDate": "2099-12-31"
        }
        try:
            res = requests.get(endpoint, headers=self.get_headers(), params=params)
            if res.status_code == 200:
                bookings = res.json()
                if bookings and isinstance(bookings, list):
                    # Extract all booking dates and find the earliest
                    dates = []
                    for b in bookings:
                        d = b.get('date')
                        if d:
                            dates.append(d)
                    if dates:
                        return sorted(dates)[0]  # Earliest booking date
            return None
        except:
            return None
            
    def fetch_visits(self, clinic_id, start_date, end_date):
        """Fetch visits for a clinic to map to bookings."""
        print(f"\nFetching Visits for clinic {clinic_id} ({start_date} to {end_date})...")
        visits_dict = {}
        res = requests.get(f"{self.base_url}/v1/clinics/{clinic_id}/visits", headers=self.get_headers(), params={"fromDate": start_date, "toDate": end_date})
        if res.status_code == 200:
            visits = res.json()
            print(f"  ✓ Fetched {len(visits)} visits")
            for v in visits:
                b_id = str(v.get('bookingId', ''))
                if b_id:
                    visits_dict[b_id] = v
        else:
            print(f"  ✗ Failed to fetch visits: {res.status_code} - {res.text}")
        return visits_dict

    def extract_and_consolidate(self, start_date, end_date):
        """Build the consolidated statistics dataframe."""
        self.fetch_base_dictionaries()
        
        bookings = self.fetch_bookings(start_date, end_date)
        if not bookings:
            print("No bookings found to extract.")
            return None
            
        clinic_id = self.clinics[0]['id'] if self.clinics else None
        
        # Pre-fetch visits to map actual visit dates
        visits_dict = self.fetch_visits(clinic_id, start_date, end_date) if clinic_id else {}
        
        data_rows = []
        
        # To avoid spamming GET Documents per patient repeatedly for same patient
        patient_remiss_cache = {}
        
        print("\nProcessing bookings data...")
        total = len(bookings)
        for idx, b in enumerate(bookings):
            if idx % 50 == 0:
                print(f"  Processed {idx}/{total}")
                
            patient = b.get('patient') or {}
            personal_number = patient.get('personalNumber')
            patient_id = patient.get('id')
            
            # Booking Patient Type
            b_pt_id = str(b.get('bookedPatientType', ''))
            b_pt_info = self.patient_types_dict.get(b_pt_id, {})
            b_pt_name = b_pt_info.get('name', b_pt_id)
            
            # FreeCard handling (Webdoc typically anchors on payment profiles or patient data)
            # Some info might reside in `patient` array, some in `paymentGroups`
            free_card = patient.get('freeCard') or {}
            free_card_from = free_card.get('validFrom', '') if isinstance(free_card, dict) else ''
            free_card_until = free_card.get('validUntil', '') if isinstance(free_card, dict) else ''
            
            # Inreferral surrogate: earliest booking date for this patient
            inreferral_date = ""
            if personal_number:
                if personal_number not in patient_remiss_cache:
                    first_date = self.fetch_patient_first_booking_date(personal_number)
                    patient_remiss_cache[personal_number] = first_date or "N/A"
                inreferral_date = patient_remiss_cache[personal_number]

            # Payment info
            payments = b.get('payments', [])
            payment_amount = sum(float(p.get('amount', 0)) for p in payments) if isinstance(payments, list) else 0

            # Action Codes
            action_code_ids = b.get('actionCodes', [])
            action_code_names = []
            for ac_id in action_code_ids:
                ac_name = self.action_codes_dict.get(str(ac_id), {}).get('code', str(ac_id))
                action_code_names.append(ac_name)

            date_val = b.get('date', '')
            time_val = b.get('startTime', '')
            appointment_datetime = f"{date_val} {time_val}".strip()

            # Map the actual visit
            visit = visits_dict.get(str(b.get('id')), {})
            actual_visit_date = visit.get('visitDate', '')

            row = {
                "Booking_ID": b.get('id'),
                "Appointment_Date": appointment_datetime,
                "Actual_Visit_Date": actual_visit_date,
                "Patient_ID": patient_id,
                "Personal_Number": personal_number,
                "Patient_FirstName": patient.get('firstName'),
                "Patient_LastName": patient.get('lastName'),
                "Booked_Patient_Type": b_pt_name,
                "First_Booking_Date (Inreferral)": inreferral_date,
                "Payment_Amount": payment_amount,
                "FreeCard_ValidFrom": free_card_from,
                "FreeCard_ValidUntil": free_card_until,
                "Action_Codes": ", ".join(action_code_names),
                "Title": b.get('title', ''),
                "Status": b.get('status', ''),
                "Arrival_Status": b.get('arrivalStatus', '')
            }
            data_rows.append(row)

        df = pd.DataFrame(data_rows)
        return df


def main():
    parser = argparse.ArgumentParser(description="Webdoc Statistics Extraction")
    parser.add_argument('--start', type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument('--end', type=str, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument('--env', type=str, default='prod', choices=['prod', 'test'], help="Environment to run against (prod or test)")
    parser.add_argument('--debug', action='store_true', help="Run without exporting files (dry-run mode for tests)")
    args = parser.parse_args()
    
    # Validate date formats
    try:
        datetime.strptime(args.start, '%Y-%m-%d')
        datetime.strptime(args.end, '%Y-%m-%d')
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format.")
        sys.exit(1)

    print("="*60)
    print(f"Statistikuttag (Webdoc API) | {args.start} to {args.end} | Env: {args.env}")
    print("="*60)
    
    extractor = WebdocStatisticsExtractor(prod_env=(args.env == 'prod'))
    
    if not extractor.authenticate():
        print("Authentication failed. Aborting.")
        sys.exit(1)
        
    df = extractor.extract_and_consolidate(args.start, args.end)
    
    if df is not None and not df.empty:
        print("\n" + "="*60)
        print(f"Dataframe compiled successfully. Total records: {len(df)}")
        print("="*60)
        
        if args.debug:
            print(df.head())
            print("\nDebug mode finished. No files exported.")
        else:
            export_dir = Path("exports")
            export_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = export_dir / f"statistikuttag_{args.start}_{args.end}_{timestamp}.csv"
            excel_path = export_dir / f"statistikuttag_{args.start}_{args.end}_{timestamp}.xlsx"
            
            try:
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                print(f"✓ Exported to CSV: {csv_path}")
                
                df.to_excel(excel_path, index=False)
                print(f"✓ Exported to Excel: {excel_path}")
            except Exception as e:
                print(f"Failed to export files: {e}")
                sys.exit(1)
    else:
        print("Extraction resulted in no data.")

if __name__ == "__main__":
    main()
