from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import devices, webdoc, schedule, exams, postal

app = FastAPI(
    title="Pulsus Holter Tracker",
    description="API for tracking Holter devices, optimizing scheduling, and integrating with Webdoc.",
    version="1.0.0",
)

# Allow CORS for the dashboard frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Should be tightened in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(devices.router, prefix="/api/v1/devices", tags=["Devices"])
app.include_router(webdoc.router, prefix="/api/v1/webdoc", tags=["Webdoc"])
app.include_router(schedule.router, prefix="/api/v1/schedule", tags=["Schedule"])
app.include_router(exams.router, prefix="/api/v1/exams", tags=["Exams"])
app.include_router(postal.router, prefix="/api/v1/postal", tags=["Postal Operations"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
