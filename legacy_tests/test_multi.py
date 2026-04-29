import sys
import os
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO

# Import existing webdoc client to leverage authentication
from app import webdoc

def main():
    print("Authenticating...")
    success, msg = webdoc.authenticate()
    if not success:
        print("Auth failed:", msg)
        return
        
    print("Creating two dummy images...")
    img1 = Image.new('RGB', (100, 100), color='red')
    img2 = Image.new('RGB', (100, 100), color='blue')
    
    img1.save('dummy1.jpg')
    img2.save('dummy2.jpg')
    
    print("Fetching clinics to get a valid clinicID...")
    clinics = webdoc.get_clinics()
    if not clinics:
        print("No clinics found")
        return
    clinic_id = clinics[0]['id']
    print(f"Using Clinic ID: {clinic_id}")
    
    url = f"{webdoc.base_url}/v1/clinics/{clinic_id}/documents"
    headers = webdoc.get_headers()
    
    print("Uploading multiple files...")
    # Passing multiple 'file' fields
    with open('dummy1.jpg', 'rb') as f1, open('dummy2.jpg', 'rb') as f2:
        files = [
            ('file', ('dummy1.jpg', f1, 'image/jpeg')),
            ('file', ('dummy2.jpg', f2, 'image/jpeg'))
        ]
        
        data = {
            'documentTypeId': '1',
            # Using a well-known test personal number format, Webdoc handles or creates it
            'personalNumber': '19121212-1212',
            'createdAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        response = requests.post(url, headers=headers, files=files, data=data)
        
        print(f"Status Code: {response.status_code}")
        try:
            print("Response:", response.json())
        except:
            print("Response Text:", response.text)

if __name__ == '__main__':
    main()
