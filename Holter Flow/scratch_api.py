"""
Fetch ALL booking types from Webdoc to find correct IDs for Holter 24h/48h/72h.
"""
import asyncio, sys
from pathlib import Path
sys.path.append(str(Path("backend").resolve()))
from app.services.webdoc_service import webdoc_client
import httpx

async def main():
    await webdoc_client.authenticate()
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{webdoc_client.base_url}/v1/bookingTypes",
            headers=webdoc_client._get_headers()
        )
        print("Status:", r.status_code)
        if r.status_code == 200:
            print("\nAll booking types:")
            for bt in r.json():
                print(f"  ID: {bt.get('id'):>4}  Name: {bt.get('name')}")

asyncio.run(main())
