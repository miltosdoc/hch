import asyncio, httpx, sys
sys.path.insert(0, '/app')

async def test():
    async with httpx.AsyncClient(timeout=180) as c:
        print("Calling webdoc-sync endpoint...")
        r = await c.post('http://localhost:8000/api/v1/exams/webdoc-sync')
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")

asyncio.run(test())
