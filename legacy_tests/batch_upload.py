"""
Webdoc Batch Upload Script
Uploads files to patients based on personnummer extracted from filename.

Filename format: The personnummer should be in the filename.
Examples:
  - 19121212-1212.jpg
  - remiss_19121212-1212.jpg
  - patient_191212121212_scan.jpg
  - 121212-1212_document.pdf

The script will extract the personnummer and upload to the matching patient.
"""

import requests
import json
import re
import sys
import os
from pathlib import Path
from datetime import datetime


class WebdocBatchUploader:
    """Batch uploader for Webdoc that extracts personnummer from filenames."""
    
    def __init__(self, client_id: str, client_secret: str, 
                 auth_url: str = "https://auth-integration.carasent.net",
                 base_url: str = "https://api-integration.carasent.net"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = auth_url
        self.base_url = base_url
        self.access_token = None
        self.clinic_id = None
        self.document_type_id = None
        
    def authenticate(self) -> bool:
        """Authenticate using OAuth2 client credentials grant."""
        token_endpoint = f"{self.auth_url}/oauth/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "documents:write patient:read patient:write document-types:read clinics:read users:read"
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
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
    
    def get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}
    
    def setup(self) -> bool:
        """Set up clinic and document type."""
        # Get clinic
        try:
            response = requests.get(f"{self.base_url}/v1/clinics", headers=self.get_headers())
            if response.status_code == 200:
                clinics = response.json()
                if clinics:
                    self.clinic_id = clinics[0].get('id')
                    print(f"✓ Using clinic: {clinics[0].get('name')} ({self.clinic_id})")
                else:
                    print("✗ No clinics found")
                    return False
        except Exception as e:
            print(f"✗ Error getting clinics: {e}")
            return False
        
        # Get document types and find "Inreferral" (Remiss) - ID: 2
        try:
            response = requests.get(f"{self.base_url}/v1/documentTypes", headers=self.get_headers())
            if response.status_code == 200:
                doc_types = response.json()
                print("\nAvailable document types:")
                for dt in doc_types:
                    status = "✓ active" if dt.get('active', True) else "✗ inactive"
                    print(f"  - ID: {dt.get('id')}, Name: {dt.get('name')} ({status})")
                
                # Look for "Inreferral" document type (ID: 2 in production)
                for dt in doc_types:
                    name = dt.get('name', '').lower()
                    if name in ['inreferral', 'remiss', 'inremiss']:
                        if dt.get('active', True):
                            self.document_type_id = dt.get('id')
                            print(f"\n✓ Using document type: {dt.get('name')} (ID: {self.document_type_id})")
                            break
                
                # If not found, try ID 2 directly (Inreferral in production)
                if not self.document_type_id:
                    for dt in doc_types:
                        if dt.get('id') == 2 and dt.get('active', True):
                            self.document_type_id = 2
                            print(f"\n✓ Using document type: {dt.get('name')} (ID: 2)")
                            break
                
                # Fallback to first active document type
                if not self.document_type_id:
                    for dt in doc_types:
                        if dt.get('active', True):
                            self.document_type_id = dt.get('id')
                            print(f"\n✓ Using document type: {dt.get('name')} (ID: {self.document_type_id})")
                            break
        except Exception as e:
            print(f"✗ Error getting document types: {e}")
            self.document_type_id = 2  # Default to Inreferral
        
        return True
    
    def extract_personnummer(self, filename: str) -> str:
        """
        Extract Swedish personnummer from filename.
        
        Handles letter suffixes like A, B, C for multiple files per patient:
        - 191212121212.jpg → 19121212-1212
        - 191212121212A.jpg → 19121212-1212
        - 191212121212B.jpg → 19121212-1212
        
        Supported formats:
        - YYYYMMDD-XXXX (e.g., 19121212-1212)
        - YYYYMMDDXXXX (e.g., 191212121212)
        - YYMMDD-XXXX (e.g., 121212-1212)
        - YYMMDDXXXX (e.g., 1212121212)
        """
        # Remove file extension
        name_without_ext = Path(filename).stem
        
        # Pattern 1: YYYYMMDD-XXXX or YYYYMMDD+XXXX (with optional letter suffix)
        match = re.search(r'((?:19|20)\d{6})[-+]?(\d{4})[A-Za-z]?(?:\D|$)', name_without_ext)
        if match:
            return f"{match.group(1)}-{match.group(2)}"
        
        # Pattern 2: 12 consecutive digits with optional letter suffix
        match = re.search(r'((?:19|20)\d{6})(\d{4})[A-Za-z]?(?:\D|$)', name_without_ext)
        if match:
            return f"{match.group(1)}-{match.group(2)}"
        
        # Pattern 3: YYMMDD-XXXX (short format with optional letter)
        match = re.search(r'(\d{6})[-+](\d{4})[A-Za-z]?(?:\D|$)', name_without_ext)
        if match:
            year_part = int(match.group(1)[:2])
            century = "19" if year_part > 30 else "20"
            return f"{century}{match.group(1)}-{match.group(2)}"
        
        # Pattern 4: 10 consecutive digits with optional letter suffix
        match = re.search(r'(\d{6})(\d{4})[A-Za-z]?(?:\D|$)', name_without_ext)
        if match:
            year_part = int(match.group(1)[:2])
            century = "19" if year_part > 30 else "20"
            return f"{century}{match.group(1)}-{match.group(2)}"
        
        return None

    def process_folder(self, folder_path: str, move_after_upload: bool = True) -> dict:
        """Process all supported files in a folder, grouped by patient."""
        folder = Path(folder_path)
        
        if not folder.exists():
            print(f"✗ Folder not found: {folder}")
            return {"processed": 0, "success": 0, "failed": 0, "skipped": 0}
        
        # Find all supported files
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.pdf', '*.gif', '*.tif', '*.tiff', '*.bmp']
        files = []
        for ext in extensions:
            files.extend(folder.glob(ext))
        
        if not files:
            print(f"No supported files found in {folder}")
            return {"processed": 0, "success": 0, "failed": 0, "skipped": 0}
        
        # Group files by personnummer
        from collections import defaultdict
        patient_files = defaultdict(list)
        skipped_files = []
        
        for file_path in files:
            personnummer = self.extract_personnummer(file_path.name)
            if personnummer:
                patient_files[personnummer].append(file_path)
            else:
                skipped_files.append(file_path)
        
        # Create processed folder if moving files
        processed_folder = folder / "processed"
        if move_after_upload:
            processed_folder.mkdir(exist_ok=True)
        
        results = {"processed": 0, "success": 0, "failed": 0, "skipped": len(skipped_files)}
        
        print(f"\nFound {len(files)} file(s) for {len(patient_files)} patient(s)")
        if move_after_upload:
            print(f"Successfully uploaded files will be moved to: {processed_folder}")
        print("-" * 60)
        
        # Process files grouped by patient
        patient_num = 0
        for personnummer, patient_file_list in sorted(patient_files.items()):
            patient_num += 1
            print(f"\n{'='*60}")
            print(f"PATIENT {patient_num}: {personnummer} ({len(patient_file_list)} file(s))")
            print("=" * 60)
            
            for i, file_path in enumerate(sorted(patient_file_list), 1):
                results["processed"] += 1
                print(f"\n  [{i}/{len(patient_file_list)}] {file_path.name}")
                
                # Upload the file
                if self.upload_file(str(file_path), personnummer):
                    results["success"] += 1
                    
                    # Move file to processed folder
                    if move_after_upload:
                        try:
                            import shutil
                            dest = processed_folder / file_path.name
                            shutil.move(str(file_path), str(dest))
                            print(f"    → Moved to: processed/{file_path.name}")
                        except Exception as e:
                            print(f"    ⚠ Could not move file: {e}")
                else:
                    results["failed"] += 1
        
        # Report skipped files
        if skipped_files:
            print(f"\n{'='*60}")
            print(f"SKIPPED ({len(skipped_files)} file(s) - no personnummer found)")
            print("=" * 60)
            for f in skipped_files:
                print(f"  ⚠ {f.name}")
        
        return results
    
    def upload_file(self, file_path: str, personal_number: str) -> bool:
        """Upload a single file to a patient."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"  ✗ File not found: {file_path}")
            return False
        
        # Check file size (max 20 MB)
        file_size = file_path.stat().st_size
        if file_size > 20 * 1024 * 1024:
            print(f"  ✗ File too large: {file_size} bytes")
            return False
        
        # Determine content type
        ext = file_path.suffix.lower()
        content_types = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.pdf': 'application/pdf',
            '.gif': 'image/gif', '.tif': 'image/tiff', '.tiff': 'image/tiff',
            '.bmp': 'image/bmp'
        }
        content_type = content_types.get(ext, 'application/octet-stream')
        
        endpoint = f"{self.base_url}/v1/clinics/{self.clinic_id}/documents"
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, content_type)}
                data = {
                    'documentTypeId': str(self.document_type_id),
                    'personalNumber': personal_number,
                    'createdAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                response = requests.post(endpoint, headers=self.get_headers(), files=files, data=data)
            
            if response.status_code in [200, 201, 202]:
                print(f"  ✓ Uploaded successfully!")
                return True
            else:
                print(f"  ✗ Upload failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"  ✗ Upload error: {e}")
            return False
    



def main():
    """Main function for batch processing."""
    
    # Configuration
    CLIENT_ID = "test-HjärtcentrumHalland"
    CLIENT_SECRET = "1ri5weun0lj4044g0sksw8os0c8wo4w"
    
    # Default folder is 'images' in the same directory as this script
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        folder_path = Path(__file__).parent / "images"
    
    print("=" * 60)
    print("Webdoc Batch Upload - Remiss Documents")
    print("=" * 60)
    print(f"\nSource folder: {folder_path}")
    
    # Initialize uploader
    uploader = WebdocBatchUploader(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    
    # Authenticate
    print("\n--- Authentication ---")
    if not uploader.authenticate():
        print("\nFailed to authenticate. Exiting.")
        sys.exit(1)
    
    # Setup (get clinic and document type)
    print("\n--- Setup ---")
    if not uploader.setup():
        print("\nFailed to setup. Exiting.")
        sys.exit(1)
    
    # Process files
    print("\n--- Processing Files ---")
    results = uploader.process_folder(str(folder_path))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total files:    {results['processed']}")
    print(f"  ✓ Successful:   {results['success']}")
    print(f"  ✗ Failed:       {results['failed']}")
    print(f"  ⚠ Skipped:      {results['skipped']}")
    print("=" * 60)
    
    if results['failed'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
