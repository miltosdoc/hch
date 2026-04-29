import requests
import re

# Read credentials
with open('api.txt', 'r', encoding='utf-8') as f:
    content = f.read()

client_id = re.search(r'ClientID:\s*(.+)', content).group(1).strip()
client_secret = re.search(r'Secret:\s*(.+)', content).group(1).strip()

# Try to authenticate WITH self-service scope
try:
    print("Requesting OAuth Token with self-service scope...")
    token_url = "https://auth.atlan.se/oauth/token"
    auth_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'patient:read patient:write self-service'
    }
    auth_res = requests.post(token_url, data=auth_data)
    
    if auth_res.status_code != 200:
        print("Auth failed:")
        print(auth_res.text)
        exit(1)
        
    access_token = auth_res.json()['access_token']
    print("Auth successful! Acquired token.")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Get Clinic ID
    clinics_res = requests.get('https://api.atlan.se/v1/clinics', headers=headers)
    if clinics_res.status_code != 200:
        print("Failed to get clinics:", clinics_res.text)
        exit(1)
    
    clinics = clinics_res.json()
    if not clinics:
        print("No clinics found!")
        exit(1)
        
    clinic_id = clinics[0]['id']
    print(f"Using Clinic ID: {clinic_id} ({clinics[0]['name']})")
    
    # Fetch visits
    visits_url = f"https://api.atlan.se/v1/clinics/{clinic_id}/visits"
    params = {
        "fromDate": "2024-01-01",
        "toDate": "2026-12-31"
    }
    
    print(f"Fetching visits from {visits_url} ...")
    visits_res = requests.get(visits_url, headers=headers, params=params)
    
    print("\n--- VISITS RESPONSE ---")
    print("Status:", visits_res.status_code)
    text = visits_res.text
    print("Response snippet:", text[:500] + ("..." if len(text) > 500 else ""))
    
except Exception as e:
    print("Exception occurred:", type(e).__name__, e)
