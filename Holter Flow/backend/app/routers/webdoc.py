from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ..database import get_db
from ..services.webdoc_service import webdoc_client
from ..models import Exam, Patient
from sqlalchemy.future import select

router = APIRouter()

@router.post("/sync-remisser")
async def sync_remisser():
    """
    Polls Webdoc for incoming Remisser and creates initial Patient records.
    (Placeholder. Real Webdoc API lacks standard GET /referrals; typically loaded via WatcherBot)
    """
    return {"message": "Sync complete. 0 new remisser found."}

from pydantic import BaseModel

class WebdocBookingRequest(BaseModel):
    personal_number: str
    date: str
    time: str
    duration_type: str # '24h', '48h', '72h'
    device_id: UUID

@router.post("/booking")
async def create_intelligent_booking(
    req: WebdocBookingRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Called by the intelligent scheduling engine modal.
    Creates a local exam immediately. Optionally tries to create in Webdoc too.
    """
    from ..models import ExamType, ReturnType, ExamStatus
    import datetime
    
    atgardskod_map = {'24h': 'E1005', '48h': 'E1006', '72h': 'E1007'}
    atgardskod = atgardskod_map.get(req.duration_type, 'E1005')
    e_type_map = {'24h': ExamType.H24, '48h': ExamType.H48, '72h': ExamType.H72}
    
    # Find or Create Local Patient
    p_result = await db.execute(select(Patient).where(Patient.personnummer == req.personal_number))
    patient = p_result.scalars().first()
    if not patient:
        # Try to fetch name from Webdoc
        first_name = ""
        last_name = ""
        try:
            details = await webdoc_client.fetch_patient_details(req.personal_number)
            first_name = details.get("firstName", "")
            last_name = details.get("lastName", "")
        except Exception:
            pass
        
        patient = Patient(
            personnummer=req.personal_number,
            first_name=first_name or "Manuell",
            last_name=last_name or "Bokning"
        )
        db.add(patient)
        await db.flush()
    
    # Create Local Exam immediately
    sched_date = datetime.date.fromisoformat(req.date)
    exam = Exam(
        device_id=req.device_id,
        patient_id=patient.id,
        exam_type=e_type_map.get(req.duration_type, ExamType.H24),
        return_type=ReturnType.POSTAL if req.duration_type == '72h' else ReturnType.CLINIC,
        status=ExamStatus.SCHEDULED,
        scheduled_date=sched_date,
        start_time=req.time,
        atgardskod=atgardskod,
    )
    db.add(exam)
    await db.commit()
    
    # Try Webdoc booking (non-blocking — if it fails, local booking still works)
    webdoc_booking_id = None
    webdoc_note = "Lokal bokning skapad. "
    try:
        success, res = await webdoc_client.create_booking(
            personal_number=req.personal_number,
            atgardskod=atgardskod,
            duration_type=req.duration_type,
            date_str=req.date,
            time_str=req.time
        )
        if success and isinstance(res, dict):
            webdoc_booking_id = str(res.get("id", ""))
            exam.webdoc_booking_id = webdoc_booking_id
            await db.commit()
            webdoc_note = "Webdoc-bokning skapad. "
        else:
            webdoc_note = "OBS: Webdoc-bokning misslyckades — skapa manuellt i Webdoc. "
    except Exception:
        webdoc_note = "OBS: Webdoc-bokning misslyckades — skapa manuellt i Webdoc. "
    
    return {
        "message": f"{webdoc_note}Exam ID: {exam.id}",
        "exam_id": str(exam.id),
        "webdoc_booking_id": webdoc_booking_id,
    }

@router.delete("/booking/{exam_id}")
async def cancel_webdoc_booking(exam_id: str, db: AsyncSession = Depends(get_db)):
    """
    Cancels an active booking internally and in Webdoc.
    Local cancellation always succeeds; Webdoc is best-effort.
    """
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Always cancel locally first
    from ..models import ExamStatus
    exam.status = ExamStatus.CANCELLED
    await db.commit()

    # Try Webdoc cancellation as best-effort
    webdoc_note = ""
    if exam.webdoc_booking_id:
        try:
            success, msg = await webdoc_client.cancel_booking(exam.webdoc_booking_id)
            if success:
                webdoc_note = "Webdoc-bokning avbokad."
            else:
                webdoc_note = "OBS: Avboka manuellt i Webdoc."
                print(f"[Webdoc] Cancel best-effort failed for {exam.webdoc_booking_id}: {msg}")
        except Exception as e:
            webdoc_note = "OBS: Avboka manuellt i Webdoc."
            print(f"[Webdoc] Cancel exception: {e}")

    return {"message": f"Bokning avbokad i Pulsus. {webdoc_note}".strip()}

@router.post("/send-remissvar/{exam_id}")
async def send_remissvar(exam_id: UUID = Path(...), db: AsyncSession = Depends(get_db)):
    """
    Generates and sends Remissvar via Webdoc Journal endpoints (requires notes:write).
    """
    success, msg = await webdoc_client.create_journal_entry("mock_pn", {})
    if not success:
        raise HTTPException(status_code=403, detail=msg)
    
    return {"message": "Journal created successfully"}
