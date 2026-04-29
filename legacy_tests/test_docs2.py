import requests
import re
import json

def get_token():
    auth_url = "https://auth.atlan.se"
    with open('api.txt', 'r', encoding='utf-8') as f:
        content = f.read()
        client_id = re.search(r'ClientID:\s*(.+)', content).group(1).strip()
        client_secret = re.search(r'Secret:\s*(.+)', content).group(1).strip()
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "documents:write patient:read document-types:read clinics:read users:read bookings:read patient-types:read actioncodes:read"
    }
    response = requests.post(f"{auth_url}/oauth/token", data=data)
    return response.json().get("access_token")

def main():
    token = get_token()
    if not token:
        print("Failed to authenticate")
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://api.atlan.se"
    
    # Get a clinic
    res_clinics = requests.get(f"{base_url}/v1/clinics", headers=headers)
    clinic_id = res_clinics.json()[0]['id']
    
    # Get a patient
    res_books = requests.get(f"{base_url}/v1/bookings", headers=headers, params={"fromDate": "2025-11-01", "toDate": "2025-11-05"})
    patient_id = None
    p_num = None
    for b in res_books.json():
        if b.get("patient") and b["patient"].get("id"):
            patient_id = b["patient"]["id"]
            p_num = b["patient"]["personalNumber"]
            break
            
    if not patient_id:
        print("No patient found to test with")
        return

    print(f"Testing with Patient ID: {patient_id}, PN: {p_num}")
    
    print(f"Testing GET /v2/patients for PN: {p_num}")
    res = requests.get(f"{base_url}/v2/patients?personalNumber={p_num}", headers=headers)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        print("SUCCESS! Output JSON:")
        print(json.dumps(res.json(), indent=2))
    else:
        print(f"Response: {res.text[:200]}")

if __name__ == "__main__":
    main()
