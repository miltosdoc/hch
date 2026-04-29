"""
Find and delete all bookings for patient 19121212-1212 (Tolvan Tolvansson).
"""
import sys, requests, json, re
from pathlib import Path
from datetime import datetime, timedelta

api_path = Path("docs/api.txt")
with open(api_path, 'r', encoding='utf-8') as f:
    content = f.read()
    client_id = re.search(r'ClientID:\s*(.+)', content).group(1).strip()
    client_secret = re.search(r'Secret:\s*(.+)', content).group(1).strip()

r = requests.post(
    "https://auth.atlan.se/oauth/token",
    data={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "documents:write patient:read patient:write document-types:read clinics:read users:read bookings:read bookings:write patient-types:read actioncodes:read"
    },
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
token = r.json()['access_token']
hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

USER_ID = "708c6212-5196-11f0-b3a0-3608e67b9fe2"
PATIENT_UUID = "96613627-3bef-11f0-a1fd-3608e67bc0b7"

# Fetch all bookings in a wide range
today = datetime.now()
# Fetch all bookings with pagination
all_bookings = []
offset = 0
while True:
    params = {
        "fromDate": "2025-01-01",
        "toDate": (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'),
        "offset": offset
    }
    resp = requests.get("https://api.atlan.se/v1/bookings", headers=hdrs, params=params)
    batch = resp.json()
    if not batch:
        break
    all_bookings.extend(batch)
    print(f"  Fetched offset={offset}, got {len(batch)} bookings")
    if len(batch) < 100:
        break
    offset += 100

print(f"Total bookings fetched: {len(all_bookings)}")

# Filter for Tolvan
tolvan_bookings = [b for b in all_bookings if (b.get('patient') or {}).get('id') == PATIENT_UUID]
print(f"Tolvan Tolvansson bookings found: {len(tolvan_bookings)}")

for b in tolvan_bookings:
    bid = b['id']
    bdate = b.get('date')
    btype = b.get('bookingType', {}).get('name')
    print(f"\n  Booking ID: {bid} | Date: {bdate} | Type: {btype}")
    
    del_resp = requests.delete(
        f"https://api.atlan.se/v1/bookings/{bid}",
        headers=hdrs,
        json={"userId": USER_ID}
    )
    print(f"  DELETE status: {del_resp.status_code} {del_resp.text}")
