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
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://api.atlan.se"
    
    res_clinics = requests.get(f"{base_url}/v1/clinics", headers=headers)
    clinic_id = res_clinics.json()[0]['id']
    
    print("Testing GET documents endpoint broadly...")
    res = requests.get(f"{base_url}/v1/clinics/{clinic_id}/documents", headers=headers, params={"limit": 5})
    if res.status_code == 200:
        docs = res.json()
        print(f"Success! Got {len(docs)} documents.")
        if docs:
            print(json.dumps(docs[0], indent=2))
    else:
        print(f"Failed to get clinic documents: {res.status_code} - {res.text}")
        
    print("\nTesting GET documents via patients logic broadly...")
    # Just grab any patient from bookings to test
    b_res = requests.get(f"{base_url}/v1/bookings", headers=headers, params={"fromDate": "2025-11-01", "toDate": "2025-11-30"})
    books = b_res.json()
    p_num = None
    for b in books:
        p = b.get("patient")
        if p and p.get("personalNumber"):
            p_num = p.get("personalNumber")
            break
            
    if p_num:
        print(f"\nTesting GET documents for personalNumber: {p_num}")
        res2 = requests.get(f"{base_url}/v1/clinics/{clinic_id}/documents", headers=headers, params={"personalNumber": p_num})
        if res2.status_code == 200:
            p_docs = res2.json()
            print(f"Success! Got {len(p_docs)} documents.")
            if p_docs:
                print(json.dumps(p_docs[0], indent=2))
        else:
            print(f"Failed to get patient documents: {res2.status_code} - {res2.text}")
            
if __name__ == "__main__":
    main()
