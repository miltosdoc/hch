import os
import httpx
from datetime import datetime
from pydantic_settings import BaseSettings

class WebdocSettings(BaseSettings):
    # Production credentials matching Integrationsportalen
    webdoc_client_id: str = os.getenv("WEBDOC_CLIENT_ID", "Kundintegration-HjärtcentrumHalland")
    webdoc_client_secret: str = os.getenv("WEBDOC_CLIENT_SECRET", "a9h9v385sb48s0w4owwggwkwg0w044o")
    webdoc_auth_url: str = os.getenv("WEBDOC_AUTH_URL", "https://auth.atlan.se")
    webdoc_api_url: str = os.getenv("WEBDOC_API_URL", "https://api.atlan.se")
    webdoc_clinic_id: str = os.getenv("WEBDOC_CLINIC_ID", "e0fb13a1-2fc5-488f-bade-e6ce8a9561b3")

settings = WebdocSettings()

class WebdocAsyncClient:
    def __init__(self):
        self.client_id = settings.webdoc_client_id
        self.client_secret = settings.webdoc_client_secret
        self.auth_url = settings.webdoc_auth_url
        self.base_url = settings.webdoc_api_url
        self.access_token = None
        self._token_obtained_at = None

    async def authenticate(self) -> bool:
        """Fetch async OAuth2 credentials from Webdoc."""
        token_endpoint = f"{self.auth_url}/oauth/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "documents:write patient:read patient:write bookings:read bookings:write document-types:read clinics:read users:read patient-types:read actioncodes:read"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    token_endpoint, 
                    data=data, 
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if response.status_code == 200:
                    self.access_token = response.json().get("access_token")
                    self._token_obtained_at = datetime.now()
                    print(f"[Webdoc] Auth OK")
                    return True
                else:
                    print(f"[Webdoc] Auth Failed ({response.status_code}): {response.text}")
                    return False
            except Exception as e:
                print(f"[Webdoc] Exception during Auth: {e}")
                return False

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def _token_expired(self) -> bool:
        """Check if token is older than 50 minutes (tokens expire at 60min)."""
        if not self._token_obtained_at:
            return True
        from datetime import timedelta
        return (datetime.now() - self._token_obtained_at) > timedelta(minutes=50)

    async def ensure_auth(self):
        if not self.access_token or self._token_expired():
            await self.authenticate()

    async def _lookup_patient_uuid(self, personal_number: str):
        """Helper to convert PN to Webdoc patient UUID."""
        await self.ensure_auth()
        endpoint = f"{self.base_url}/v2/patients"
        clean_pn = personal_number.replace("-", "")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint, 
                headers=self._get_headers(), 
                params={"personalNumber": personal_number}
            )
            if response.status_code == 200:
                patients = response.json()
                if patients and isinstance(patients, list):
                    # Match on cleaned personnummer
                    for p in patients:
                        if p.get('personalNumber', '').replace('-', '') == clean_pn:
                            return p.get("id")
                    # Fallback: return first match
                    return patients[0].get("id")
                elif isinstance(patients, dict):
                    return patients.get("id")
            print(f"[Webdoc] Patient lookup failed for {personal_number}: {response.status_code}")
            return None

    async def fetch_patient_details(self, personal_number: str) -> dict:
        """Fetch patient details including city/postort from Webdoc."""
        await self.ensure_auth()
        if not self.access_token:
            return {}
        
        # Use /v2/patients endpoint with personalNumber query (same as _lookup_patient_uuid)
        endpoint = f"{self.base_url}/v2/patients"
        clean_pn = personal_number.replace("-", "")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers=self._get_headers(),
                    params={"personalNumber": personal_number}
                )
                print(f"[Webdoc] Patient details for {personal_number}: status={response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    # Response is a list — find matching patient
                    data = None
                    if isinstance(result, list) and result:
                        for p in result:
                            if p.get('personalNumber', '').replace('-', '') == clean_pn:
                                data = p
                                break
                        if not data:
                            data = result[0]
                    elif isinstance(result, dict):
                        data = result
                    
                    if data:
                        addr = data.get("address") or {}
                        city = addr.get("city", "") if isinstance(addr, dict) else ""
                        print(f"[Webdoc] Patient {personal_number} → city={city}")
                        return {
                            "city": city,
                            "address": addr.get("streetName", "") if isinstance(addr, dict) else "",
                            "zipCode": addr.get("zipCode", "") if isinstance(addr, dict) else "",
                        }
                else:
                    print(f"[Webdoc] Patient details response ({response.status_code}): {response.text[:200]}")
            except Exception as e:
                print(f"[Webdoc] Patient details fetch failed for {personal_number}: {e}")
        return {}

    async def create_patient(self, personal_number: str, patient_type: str = "Vårdavtal Kardiologi"):
        """Create a new patient in Webdoc via SPAR integration."""
        await self.ensure_auth()
        if not self.access_token:
            return False, "Not authenticated"
            
        endpoint = f"{self.base_url}/v1/patients"
        payload = {
            "personalNumber": personal_number,
            "patientType": patient_type
        }
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    endpoint,
                    headers=self._get_headers(),
                    json=payload
                )
                if response.status_code in [200, 201, 204]:
                    return True, response.json() if response.text else {}
                else:
                    return False, response.text
            except Exception as e:
                return False, str(e)

    async def fetch_bookings(self, from_date: str, to_date: str):
        """Fetch all bookings from Webdoc in a date range with pagination."""
        await self.ensure_auth()
        if not self.access_token:
            return []
        
        results = []
        offset = 0
        limit = 100
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                params = {
                    "fromDate": from_date,
                    "toDate": to_date,
                    "offset": offset,
                }
                try:
                    response = await client.get(
                        f"{self.base_url}/v1/bookings",
                        headers=self._get_headers(),
                        params=params
                    )
                    if response.status_code == 200:
                        bookings = response.json()
                        results.extend(bookings)
                        print(f"[Webdoc] Fetched {len(bookings)} bookings (offset={offset})")
                        if len(bookings) < limit:
                            break
                        offset += limit
                    else:
                        print(f"[Webdoc] Booking fetch failed: {response.status_code} {response.text}")
                        break
                except Exception as e:
                    print(f"[Webdoc] Exception during booking fetch: {e}")
                    break
        
        return results

    _cached_user_info = None

    async def _get_default_user_info(self):
        """Fetch the first active user and their clinic to use as the creator."""
        if self._cached_user_info:
            return self._cached_user_info
        await self.ensure_auth()
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(f"{self.base_url}/v1/users", headers=self._get_headers())
                if res.status_code == 200 and res.json():
                    user = res.json()[0]
                    user_id = user.get("id")
                    clinic_id = settings.webdoc_clinic_id
                    if user.get("clinics") and len(user["clinics"]) > 0:
                        clinic_id = user["clinics"][0].get("id", settings.webdoc_clinic_id)
                    
                    self._cached_user_info = (user_id, clinic_id)
                    return self._cached_user_info
            except Exception as e:
                print(f"[Webdoc] Failed to fetch standard user: {e}")
        return ("5fbf1078-3bf3-11f0-925f-3608e67bd007", settings.webdoc_clinic_id)  # Fallbacks

    async def create_booking(self, personal_number: str, atgardskod: str, duration_type: str, date_str: str, time_str: str = "08:00"):
        """
        Creates a booking on the Webdoc API for E1005 / E1006 / E1007
        """
        await self.ensure_auth()
        if not self.access_token:
            return False, "Failed to authenticate with Webdoc"
            
        endpoint = f"{self.base_url}/v1/bookings"
        
        # Look up patient UUID
        patient_uuid = await self._lookup_patient_uuid(personal_number)
        
        # If patient doesn't exist, create it via SPAR integration
        if not patient_uuid:
            success, _ = await self.create_patient(personal_number)
            if not success:
                return False, "Patient not found in Webdoc and could not be created automatically."
            # Refetch the UUID after creation
            patient_uuid = await self._lookup_patient_uuid(personal_number)
            if not patient_uuid:
               return False, "Patient was created but UUID retrieval failed."

        # Map booking type ID
        booking_type_map = {"24h": 9, "48h": 10, "72h": 11}
        booking_type_id = booking_type_map.get(duration_type, 9)

        user_id, clinic_id = await self._get_default_user_info()

        # Calculate end_time
        try:
            from datetime import datetime, timedelta
            start_dt = datetime.strptime(time_str, "%H:%M")
            end_dt = start_dt + timedelta(minutes=15)
            end_time_str = end_dt.strftime("%H:%M")
        except:
            end_time_str = "08:15"

        payload = {
            "userId": user_id,
            "clinicId": clinic_id,
            "bookingTypeId": int(booking_type_id),
            "date": date_str,
            "startTime": time_str,
            "endTime": end_time_str,
            "patientId": patient_uuid,
            "allowOverlap": True,
            "note": "Automated Booking via Pulsus Holter Tracking"
        }

        
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, headers=self._get_headers(), json=payload)
            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                print(f"[Webdoc Error] create_booking failed {response.status_code}: {response.text}")
                return False, response.text

    async def cancel_booking(self, booking_id: str):
        """Cancels an existing booking in Webdoc."""
        await self.ensure_auth()
        if not self.access_token:
            return False, "Failed to authenticate with Webdoc"
            
        endpoint = f"{self.base_url}/v1/bookings/{booking_id}"
        
        user_id, _ = await self._get_default_user_info()

        # Often Webdoc requires userId to identify who is making the change
        payload = {"status": "cancelled", "userId": user_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(endpoint, headers=self._get_headers(), json=payload)
            if response.status_code in [200, 204]:
                return True, "Booking cancelled"
            else:
                print(f"[Webdoc Error] cancel_booking failed {response.status_code}: {response.text}")
                # Sometimes APIs use DELETE instead of PATCH status
                if response.status_code in [400, 405, 500]:
                    try:
                        del_res = await client.delete(endpoint, headers=self._get_headers())
                        if del_res.status_code in [200, 204]:
                            return True, "Booking deleted via fallback"
                    except:
                        pass
                return False, response.text

    async def create_journal_entry(self, personal_number: str, exam_metadata: dict):
        """
        Submits structural results back to Webdoc (Remissvar / Notes).
        Requires notes:write scope (Currently unavailable).
        """
        return False, "notes:write scope is not authorized on current exact credentials."

webdoc_client = WebdocAsyncClient()
