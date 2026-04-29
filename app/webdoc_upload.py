"""
Webdoc API Integration Script
Uploads JPG files to a patient's record in Webdoc.
"""

import requests
import json
import base64
import os
from pathlib import Path
from datetime import datetime


class WebdocClient:
    """Client for interacting with the Webdoc API."""
    
    def __init__(self, client_id: str, client_secret: str, base_url: str = "https://api.atlan.se", auth_url: str = "https://auth.atlan.se"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.auth_url = auth_url
        self.access_token = None
        
    def authenticate(self) -> bool:
        """
        Authenticate using OAuth2 client credentials grant.
        Returns True if authentication successful.
        Tries multiple authentication methods to handle various API configurations.
        """
        token_endpoint = f"{self.auth_url}/oauth/token"
        
        print(f"Authenticating with Webdoc API...")
        print(f"Token endpoint: {token_endpoint}")
        print(f"Client ID: {self.client_id}")
        
        # Method 1: Standard form-urlencoded with credentials in body
        print("\n--- Trying Method 1: Form-encoded body ---")
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "documents:write patient:read document-types:read clinics:read users:read"
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            response = requests.post(token_endpoint, data=data, headers=headers)
            print(f"Method 1 response status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                print("✓ Authentication successful!")
                return True
            else:
                print(f"Method 1 failed: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Method 1 error: {e}")
        
        # Method 2: Using Basic Auth header with client credentials
        print("\n--- Trying Method 2: Basic Auth header ---")
        import base64
        credentials = f"{self.client_id}:{self.client_secret}"
        credentials_b64 = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        headers_basic = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials_b64}"
        }
        
        data_basic = {
            "grant_type": "client_credentials",
            "scope": "documents:write patient:read document-types:read"
        }
        
        try:
            response = requests.post(token_endpoint, data=data_basic, headers=headers_basic)
            print(f"Method 2 response status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                print("✓ Authentication successful!")
                return True
            else:
                print(f"Method 2 failed: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Method 2 error: {e}")
        
        # Method 3: Try without scope (minimal request)
        print("\n--- Trying Method 3: Without scope ---")
        data_no_scope = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(token_endpoint, data=data_no_scope, headers=headers)
            print(f"Method 3 response status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                print("✓ Authentication successful!")
                return True
            else:
                print(f"Method 3 failed: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Method 3 error: {e}")
        
        # Method 4: Try JSON body instead of form-encoded
        print("\n--- Trying Method 4: JSON body ---")
        headers_json = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(token_endpoint, json=data, headers=headers_json)
            print(f"Method 4 response status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                print("✓ Authentication successful!")
                return True
            else:
                print(f"Method 4 failed: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Method 4 error: {e}")
        
        print("\n✗ All authentication methods failed.")
        print("\nPlease verify:")
        print("1. The Client ID is correct (including any special characters)")
        print("2. The Client Secret is correct")  
        print("3. The credentials are active and properly configured in Webdoc")
        return False
    
    def get_headers(self) -> dict:
        """Get headers with authorization token."""
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")
        return {
            "Authorization": f"Bearer {self.access_token}"
        }
    
    def get_document_types(self) -> list:
        """Fetch available document types from the API."""
        endpoint = f"{self.base_url}/v1/documentTypes"
        
        try:
            print(f"\nFetching document types...")
            response = requests.get(endpoint, headers=self.get_headers())
            
            if response.status_code == 200:
                doc_types = response.json()
                print(f"✓ Found {len(doc_types)} document types")
                return doc_types
            else:
                print(f"✗ Failed to get document types: {response.status_code}")
                print(f"Response: {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error fetching document types: {e}")
            return []
    
    def get_clinics(self) -> list:
        """Fetch available clinics from the API."""
        endpoint = f"{self.base_url}/v1/clinics"
        
        try:
            print(f"\nFetching clinics...")
            response = requests.get(endpoint, headers=self.get_headers())
            
            if response.status_code == 200:
                clinics = response.json()
                print(f"✓ Found {len(clinics)} clinic(s)")
                return clinics
            else:
                print(f"✗ Failed to get clinics: {response.status_code}")
                print(f"Response: {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error fetching clinics: {e}")
            return []
    
    def get_users(self) -> list:
        """Fetch available users from the API."""
        endpoint = f"{self.base_url}/v1/users"
        
        try:
            print(f"\nFetching users...")
            response = requests.get(endpoint, headers=self.get_headers())
            
            if response.status_code == 200:
                users = response.json()
                print(f"✓ Found {len(users)} user(s)")
                return users
            else:
                print(f"✗ Failed to get users: {response.status_code}")
                print(f"Response: {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error fetching users: {e}")
            return []
    
    def get_patient_by_personal_number(self, personal_number: str) -> dict:
        """
        Get patient information by personal number.
        Personal number format: YYYYMMDD-XXXX (Swedish format)
        """
        # Remove dashes for API call (some APIs prefer without dash)
        clean_pn = personal_number.replace("-", "")
        
        endpoint = f"{self.base_url}/v2/patients"
        params = {"personalNumber": personal_number}
        
        try:
            print(f"\nLooking up patient with personal number: {personal_number}")
            response = requests.get(endpoint, headers=self.get_headers(), params=params)
            
            if response.status_code == 200:
                patients = response.json()
                if patients:
                    print(f"✓ Found patient")
                    return patients[0] if isinstance(patients, list) else patients
                else:
                    print("✗ No patient found with that personal number")
                    return None
            else:
                print(f"✗ Failed to lookup patient: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error looking up patient: {e}")
            return None
    
    def upload_document(self, clinic_id: str, personal_number: str, file_path: str, 
                        document_type_id: int = 1, user_id: str = None) -> bool:
        """
        Upload a document (e.g. JPG file) to a patient's record.
        Uses the /v1/clinics/:clinicId/documents endpoint with multipart/form-data.
        
        Args:
            clinic_id: The clinic UUID to upload to
            personal_number: Patient's Swedish personal number (YYYYMMDD-XXXX)
            file_path: Path to the file to upload
            document_type_id: Document type ID (default: 1 for "Dokument")
            user_id: Optional user UUID for the caregiver
            
        Returns:
            True if upload successful, False otherwise
        """
        endpoint = f"{self.base_url}/v1/clinics/{clinic_id}/documents"
        
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"✗ File not found: {file_path}")
            return False
        
        # Get file size
        file_size = file_path.stat().st_size
        max_size = 20 * 1024 * 1024  # 20 MB limit
        if file_size > max_size:
            print(f"✗ File too large: {file_size} bytes (max: {max_size} bytes)")
            return False
        
        # Determine content type
        extension = file_path.suffix.lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.pdf': 'application/pdf',
            '.gif': 'image/gif',
            '.tga': 'image/tga',
            '.tif': 'image/tiff',
            '.tiff': 'image/tiff',
            '.bmp': 'image/bmp',
            '.xcf': 'image/x-xcf'
        }
        content_type = content_types.get(extension, 'application/octet-stream')
        
        # Prepare multipart form data
        headers = self.get_headers()
        # Don't set Content-Type - requests will handle it for multipart
        
        print(f"\nUploading document: {file_path.name}")
        print(f"Endpoint: {endpoint}")
        print(f"Patient personal number: {personal_number}")
        print(f"Document type ID: {document_type_id}")
        print(f"Content type: {content_type}")
        print(f"File size: {file_size} bytes")
        
        try:
            with open(file_path, 'rb') as f:
                files = {
                    'file': (file_path.name, f, content_type)
                }
                data = {
                    'documentTypeId': str(document_type_id),
                    'personalNumber': personal_number,
                    'createdAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                if user_id:
                    data['userId'] = user_id
                
                response = requests.post(endpoint, headers=headers, files=files, data=data)
            
            print(f"Upload response status: {response.status_code}")
            
            if response.status_code in [200, 201, 202]:
                print(f"✓ Document uploaded successfully!")
                try:
                    result = response.json()
                    if result:
                        print(f"Response: {json.dumps(result, indent=2)}")
                except:
                    pass
                return True
            else:
                print(f"✗ Upload failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Upload error: {e}")
            return False


def main():
    """Main function to demonstrate the Webdoc API integration."""
    
    # Configuration - using the provided credentials
    CLIENT_ID = "YOUR_CLIENT_ID"
    CLIENT_SECRET = "YOUR_CLIENT_SECRET"
    
    # Test patient personal number
    PATIENT_PERSONAL_NUMBER = "19121212-1212"
    
    # List of environments to try (from official Webdoc documentation)
    environments = [
        # Test/Integration environment (most likely for test- prefixed credentials!)
        {"name": "Integration/Test", "auth_url": "https://auth-integration.carasent.net", "base_url": "https://api-integration.carasent.net"},
        # Production environment
        {"name": "Production", "auth_url": "https://auth.atlan.se", "base_url": "https://api.atlan.se"},
    ]
    
    print("=" * 60)
    print("Webdoc API Integration Test")
    print("=" * 60)
    
    client = None
    
    # Try each environment
    for env in environments:
        print(f"\n{'='*60}")
        print(f"Trying environment: {env['name']}")
        print(f"Auth URL: {env['auth_url']}")
        print(f"API URL: {env['base_url']}")
        print("=" * 60)
        
        client = WebdocClient(
            client_id=CLIENT_ID, 
            client_secret=CLIENT_SECRET,
            auth_url=env['auth_url'],
            base_url=env['base_url']
        )
        
        if client.authenticate():
            print(f"\n✓ Successfully connected to {env['name']}!")
            break
        else:
            print(f"\n✗ Could not authenticate with {env['name']}")
            client = None
    
    if not client or not client.access_token:
        print("\n" + "=" * 60)
        print("Failed to authenticate with any environment.")
        print("=" * 60)
        print("\nPlease verify:")
        print("1. The Client ID and Secret are correct")
        print("2. The credentials are active and not expired")
        print("3. Your network can reach the Webdoc API servers")
        print("\nYou may need to contact Webdoc/Carasent support for the correct API endpoint.")
        return
    
    # Step 2: Get document types (optional, for reference)
    doc_types = client.get_document_types()
    if doc_types:
        print("\nAvailable document types:")
        for dt in doc_types[:5]:  # Show first 5
            print(f"  - ID: {dt.get('id')}, Name: {dt.get('name')}")
    
    # Step 3: Get clinics (required for document upload)
    clinics = client.get_clinics()
    if not clinics:
        print("\n✗ No clinics found. Cannot upload documents without a clinic ID.")
        return
    
    # Use the first clinic (or you can select a specific one)
    clinic = clinics[0]
    clinic_id = clinic.get('id')
    clinic_name = clinic.get('name', 'Unknown')
    print(f"\nUsing clinic: {clinic_name} (ID: {clinic_id})")
    
    # Step 4: Look up the patient
    patient = client.get_patient_by_personal_number(PATIENT_PERSONAL_NUMBER)
    if patient:
        print(f"\nPatient info: {json.dumps(patient, indent=2)}")
    
    # Step 5: Upload JPG files
    # Look for JPG files in the images folder
    jpg_folder = Path(__file__).parent / "images"
    if not jpg_folder.exists():
        jpg_folder.mkdir(exist_ok=True)
        print(f"\nCreated folder for images: {jpg_folder}")
        print("Please add JPG files to this folder and run the script again.")
    else:
        # Support multiple image formats
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.pdf', '*.gif']:
            image_files.extend(jpg_folder.glob(ext))
        
        if not image_files:
            print(f"\nNo image files found in {jpg_folder}")
            print("Please add image files (jpg, jpeg, png, pdf, gif) to upload.")
        else:
            print(f"\nFound {len(image_files)} file(s) to upload:")
            for img_file in image_files:
                print(f"  - {img_file.name}")
            
            # Upload each file
            success_count = 0
            for img_file in image_files:
                success = client.upload_document(
                    clinic_id=clinic_id,
                    personal_number=PATIENT_PERSONAL_NUMBER,
                    file_path=str(img_file),
                    document_type_id=1  # "Dokument" as default
                )
                if success:
                    success_count += 1
            
            print(f"\n✓ Successfully uploaded {success_count}/{len(image_files)} files")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

