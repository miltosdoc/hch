import requests
import re

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
        "scope": "bookings:read clinics:read documents:write patient:read document-types:read users:read patient-types:read actioncodes:read"
    }
    response = requests.post(f"{auth_url}/oauth/token", data=data)
    return response.json().get("access_token")

def main():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://api.atlan.se"
    
    # Let's hit /v1/bookings with various parameter names
    param_sets = [
        {"from": "2025-11-01 00:00:00", "to": "2025-11-30 23:59:59"},
        {"fromDate": "2025-11-01", "toDate": "2025-11-30"},
        {"startDate": "2025-11-01", "endDate": "2025-11-30"},
        {"startTime": "2025-11-01 00:00:00", "endTime": "2025-11-30 23:59:59"},
        {"start_date": "2025-11-01", "end_date": "2025-11-30"},
        {"timeFrom": "2025-11-01 00:00:00", "timeTo": "2025-11-30 23:59:59"},
        {"timeFrom": "2025-11-01", "timeTo": "2025-11-30"},
        {"start": "2025-11-01", "end": "2025-11-30"}
    ]
    
    res_clinics = requests.get(f"{base_url}/v1/clinics", headers=headers)
    clinic_id = res_clinics.json()[0]['id']
    print(f"Testing /v1/clinics/{clinic_id}/bookings...")
    for params in param_sets:
        res = requests.get(f"{base_url}/v1/clinics/{clinic_id}/bookings", headers=headers, params=params)
        if res.status_code == 200:
            books = res.json()
            if books:
                first_date = books[0].get('time', 'Unknown')
                print(f"Params {list(params.keys())} -> Count: {len(books)}, First Book Date: {first_date}")
            else:
                print(f"Params {list(params.keys())} -> Count: {len(books)}")
        else:
            print(f"Error {res.status_code}: {res.text}")
if __name__ == "__main__":
    main()
