import asyncio
import sys
import httpx
from pathlib import Path

# Add backend directory to path so we can import the service
sys.path.append(str(Path("backend").resolve()))
from app.services.webdoc_service import webdoc_client

async def fetch_booking_types():
    await webdoc_client.authenticate()
    
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{webdoc_client.base_url}/v1/bookingTypes", 
            headers=webdoc_client._get_headers()
        )
        print("Status:", r.status_code)
        
        if r.status_code == 200:
            for bt in r.json():
                if "remiss" in str(bt.get("name", "")).lower():
                    print("- ID:", bt.get("id"), "NAME:", bt.get("name"))
        else:
            print(r.text)

asyncio.run(fetch_booking_types())
