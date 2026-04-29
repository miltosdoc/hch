from fastapi import APIRouter, Depends, HTTPException, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Dict, Optional
from datetime import date, timedelta, datetime
from uuid import UUID
from pydantic import BaseModel

from ..database import get_db
from ..models import Exam, ExamStatus, ExamType, ReturnType, Patient, Device, DeviceStatus
from ..services.webdoc_service import webdoc_client

router = APIRouter()


def get_effective_duration(exam) -> int:
    """Return the effective duration in days, considering custom override."""
    if exam.duration_days:
        return exam.duration_days
    return {"24h": 1, "48h": 2, "72h": 3}.get(
        exam.exam_type.value if exam.exam_type else "24h", 1
    )

# Map Webdoc bookingType names to our ExamType
HOLTER_BOOKING_TYPES = {
    "holter 24h": ExamType.H24,
    "holter 48h": ExamType.H48,
    "holter 72h": ExamType.H72,
    "ukg + holter": ExamType.H24,  # Combo UKG+Holter defaults to 24h
}

ATGARDSKOD_MAP = {ExamType.H24: "E1005", ExamType.H48: "E1006", ExamType.H72: "E1007"}


@router.get("")
async def get_all_exams(db: AsyncSession = Depends(get_db)):
    """Retrieve all exams mapping dynamically to the UI calendar."""
    result = await db.execute(
        select(Exam, Patient, Device)
        .join(Patient, Exam.patient_id == Patient.id)
        .join(Device, Exam.device_id == Device.id)
    )
    rows = result.all()
    
    formatted = []
    for exam, patient, device in rows:
        formatted.append({
            "id": str(exam.id),
            "device_id": str(device.id),
            "device_code": device.device_code,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_pn": patient.personnummer,
            "patient_city": patient.city or "",
            "exam_type": exam.exam_type.value if exam.exam_type else None,
            "status": exam.status.value if exam.status else None,
            "scheduled_date": exam.scheduled_date.isoformat() if exam.scheduled_date else None,
            "start_time": exam.start_time or None,
            "expected_removal_at": exam.expected_removal_at.isoformat() if exam.expected_removal_at else None,
            "expected_return_at": exam.expected_return_at.isoformat() if exam.expected_return_at else None,
            "webdoc_booking_id": exam.webdoc_booking_id,
            "atgardskod": exam.atgardskod,
            "return_type": exam.return_type.value if exam.return_type else None,
            "started_at": exam.started_at.isoformat() if exam.started_at else None,
            "actual_return_at": exam.actual_return_at.isoformat() if exam.actual_return_at else None,
            "duration_days": get_effective_duration(exam),
        })
    return formatted


@router.get("/active-clinic")
async def get_active_clinic_exams(db: AsyncSession = Depends(get_db)):
    """Return all currently checked-out clinic (fysiskt besök) exams."""
    from datetime import datetime as dt
    result = await db.execute(
        select(Exam, Patient, Device)
        .join(Patient, Exam.patient_id == Patient.id)
        .join(Device, Exam.device_id == Device.id)
        .where(Exam.status == ExamStatus.ACTIVE)
    )
    rows = result.all()
    
    formatted = []
    for exam, patient, device in rows:
        duration_days = {"24h": 1, "48h": 2, "72h": 3}.get(
            exam.exam_type.value if exam.exam_type else "24h", 1
        )
        days_out = (dt.utcnow() - exam.started_at).days if exam.started_at else 0
        expected_back = exam.expected_return_at.isoformat() if exam.expected_return_at else None
        
        formatted.append({
            "exam_id": str(exam.id),
            "device_id": str(device.id),
            "device_code": device.device_code,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_pn": patient.personnummer,
            "patient_city": patient.city or "",
            "exam_type": exam.exam_type.value if exam.exam_type else None,
            "scheduled_date": exam.scheduled_date.isoformat() if exam.scheduled_date else None,
            "started_at": exam.started_at.isoformat() if exam.started_at else None,
            "expected_return_at": expected_back,
            "days_out": days_out,
            "duration_days": duration_days,
        })
    return formatted


class ReassignRequest(BaseModel):
    new_device_id: UUID


@router.patch("/{exam_id}/reassign")
async def reassign_device(
    exam_id: UUID = Path(...),
    body: ReassignRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Reassign an exam to a different Holter device.
    If the target device has a conflicting exam on overlapping dates,
    automatically swap devices between the two exams.
    """
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Verify the new device exists
    dev_result = await db.execute(select(Device).where(Device.id == body.new_device_id))
    device = dev_result.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    old_device_id = exam.device_id
    
    # Calculate the date range this exam occupies
    duration_days = {"24h": 1, "48h": 2, "72h": 3}.get(
        exam.exam_type.value if exam.exam_type else "24h", 1
    )
    exam_start = exam.scheduled_date
    exam_end = exam_start + timedelta(days=duration_days) if exam_start else exam_start
    
    # Check for conflicting exams on the target device
    swapped_exam = None
    if exam_start:
        conflict_query = select(Exam).where(
            Exam.device_id == body.new_device_id,
            Exam.id != exam_id,
            Exam.status.in_([ExamStatus.SCHEDULED, ExamStatus.ACTIVE]),
        )
        conflict_result = await db.execute(conflict_query)
        conflicts = conflict_result.scalars().all()
        
        for c in conflicts:
            c_duration = {"24h": 1, "48h": 2, "72h": 3}.get(
                c.exam_type.value if c.exam_type else "24h", 1
            )
            c_start = c.scheduled_date
            c_end = c_start + timedelta(days=c_duration) if c_start else c_start
            
            # Check date overlap
            if c_start and exam_start and c_end and exam_end:
                if c_start < exam_end and exam_start < c_end:
                    # Conflict! Swap: give the conflicting exam our old device
                    c.device_id = old_device_id
                    swapped_exam = c
                    break
    
    # Perform the reassignment
    exam.device_id = body.new_device_id
    await db.commit()
    
    response = {
        "message": f"Exam reassigned to {device.device_code}",
        "exam_id": str(exam_id),
        "old_device_id": str(old_device_id),
        "new_device_id": str(body.new_device_id),
        "new_device_code": device.device_code,
    }
    
    if swapped_exam:
        # Get the old device code for the swap message
        old_dev_result = await db.execute(select(Device).where(Device.id == old_device_id))
        old_device = old_dev_result.scalars().first()
        old_code = old_device.device_code if old_device else "unknown"
        response["swapped"] = {
            "exam_id": str(swapped_exam.id),
            "moved_to_device": old_code,
        }
        response["message"] += f" (bytte plats med annan bokning → {old_code})"
    
    return response


class SetReturnTypeRequest(BaseModel):
    return_type: str  # "clinic" or "postal"


@router.patch("/{exam_id}/return-type")
async def set_return_type(
    exam_id: UUID = Path(...),
    body: SetReturnTypeRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Set whether an exam's device is returned via post or clinic visit."""
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    try:
        exam.return_type = ReturnType(body.return_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid return_type. Must be 'clinic' or 'postal'")
    
    await db.commit()
    return {"message": f"Return type set to {body.return_type}", "exam_id": str(exam_id)}


class SetDurationRequest(BaseModel):
    duration_days: int  # 1-7


@router.patch("/{exam_id}/duration")
async def set_duration(
    exam_id: UUID = Path(...),
    body: SetDurationRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Set custom measurement duration in days (1-7). Overrides exam_type default."""
    if not 1 <= body.duration_days <= 7:
        raise HTTPException(status_code=400, detail="Duration must be between 1 and 7 days")
    
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    exam.duration_days = body.duration_days
    await db.commit()
    return {
        "message": f"Duration set to {body.duration_days} days",
        "exam_id": str(exam_id),
        "duration_days": body.duration_days,
    }

class PostponeRequest(BaseModel):
    new_return_date: str  # ISO date string e.g. "2026-04-20"


@router.patch("/{exam_id}/postpone")
async def postpone_return(
    exam_id: UUID = Path(...),
    body: PostponeRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Postpone the expected return date for an active exam."""
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    try:
        new_date = date.fromisoformat(body.new_return_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    if new_date < date.today():
        raise HTTPException(status_code=400, detail="New return date cannot be in the past")
    
    exam.expected_return_at = new_date
    await db.commit()
    return {
        "message": f"Return postponed to {body.new_return_date}",
        "exam_id": str(exam_id),
        "expected_return_at": new_date.isoformat(),
    }


@router.post("/{exam_id}/checkout")
async def checkout_exam(
    exam_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """Check out a device to the patient (always at the clinic).
    Sets exam to ACTIVE, device to ON_PATIENT, and calculates expected dates.
    """
    from datetime import datetime as dt
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    if exam.status != ExamStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail=f"Exam is already {exam.status.value}, cannot checkout")
    
    dev_result = await db.execute(select(Device).where(Device.id == exam.device_id))
    device = dev_result.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.status not in (DeviceStatus.AVAILABLE, DeviceStatus.ASSIGNED):
        raise HTTPException(status_code=400, detail=f"Device {device.device_code} is {device.status.value}, not available for checkout")
    
    now = dt.utcnow()
    duration_days = get_effective_duration(exam)
    
    exam.status = ExamStatus.ACTIVE
    exam.started_at = now
    exam.expected_removal_at = (date.today() + timedelta(days=duration_days))
    
    # For postal returns: expected_return = removal + 3 business days
    if exam.return_type == ReturnType.POSTAL:
        removal_date = exam.expected_removal_at
        transit_days = 0
        current = removal_date
        while transit_days < 3:
            current = current + timedelta(days=1)
            if current.weekday() < 5:  # Mon–Fri
                transit_days += 1
        exam.expected_return_at = current
    else:
        exam.expected_return_at = exam.expected_removal_at
    
    device.status = DeviceStatus.ON_PATIENT
    
    await db.commit()
    return {
        "message": f"Utcheckad: {device.device_code} till patient",
        "exam_id": str(exam_id),
        "device_code": device.device_code,
        "expected_removal_at": exam.expected_removal_at.isoformat() if exam.expected_removal_at else None,
        "expected_return_at": exam.expected_return_at.isoformat() if exam.expected_return_at else None,
    }


@router.post("/{exam_id}/checkin")
async def checkin_exam(
    exam_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """Check in a device when it comes back from the patient (any return method).
    Sets exam to COMPLETED, device to AVAILABLE.
    """
    from datetime import datetime as dt
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    dev_result = await db.execute(select(Device).where(Device.id == exam.device_id))
    device = dev_result.scalars().first()
    
    exam.status = ExamStatus.COMPLETED
    exam.actual_return_at = dt.utcnow()
    if not exam.actual_removal_at:
        exam.actual_removal_at = dt.utcnow()
    device.status = DeviceStatus.AVAILABLE
    
    await db.commit()
    return {
        "message": f"Incheckad: {device.device_code}",
        "exam_id": str(exam_id),
        "device_code": device.device_code,
    }


@router.post("/{exam_id}/reactivate")
async def reactivate_exam(
    exam_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """Reactivate a completed exam back to scheduled status.
    Useful when an exam was accidentally completed or needs to be reopened.
    """
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalars().first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    dev_result = await db.execute(select(Device).where(Device.id == exam.device_id))
    device = dev_result.scalars().first()
    
    exam.status = ExamStatus.SCHEDULED
    exam.started_at = None
    exam.actual_removal_at = None
    exam.actual_return_at = None
    exam.expected_removal_at = None
    exam.expected_return_at = None
    
    if device:
        device.status = DeviceStatus.AVAILABLE
    
    await db.commit()
    return {
        "message": f"Reaktiverad: bokning återställd till schemalagd",
        "exam_id": str(exam_id),
        "device_code": device.device_code if device else "unknown",
    }

@router.post("/webdoc-sync")
async def sync_webdoc_exams(db: AsyncSession = Depends(get_db)):
    """
    Fetches bookings from Webdoc API, filters for Holter-related booking types
    (Holter 24h, Holter 48h, Holter 72h), and upserts them into the local scheduling pipeline.
    """
    from_date = date.today().isoformat()
    to_date = (date.today() + timedelta(days=30)).isoformat()
    
    bookings = await webdoc_client.fetch_bookings(from_date, to_date)
    
    if not bookings:
        return {"message": "Webdoc sync complete. 0 bookings found.", "new": 0, "cancelled": 0}
    
    new_count = 0
    cancel_count = 0
    
    dev_result = await db.execute(select(Device))
    all_devices = dev_result.scalars().all()
    
    for b in bookings:
        booking_type_obj = b.get("bookingType") or {}
        booking_type_name = (booking_type_obj.get("name") or "").lower().strip()
        booking_id = str(b.get("id", ""))
        booking_date_str = b.get("date", "")
        booking_start_time = b.get("startTime", "")
        
        exam_type = HOLTER_BOOKING_TYPES.get(booking_type_name)
        if not exam_type:
            continue
        
        existing = await db.execute(
            select(Exam).where(Exam.webdoc_booking_id == booking_id)
        )
        existing_exam = existing.scalars().first()
        
        # Update existing exams: sync exam_type, start_time, city
        if existing_exam:
            if not existing_exam.start_time and booking_start_time:
                existing_exam.start_time = booking_start_time
            # Sync exam_type changes from Webdoc (only if no custom duration set)
            if existing_exam.exam_type != exam_type and not existing_exam.duration_days:
                existing_exam.exam_type = exam_type
            # Sync scheduled date changes
            if booking_date_str:
                try:
                    new_date = date.fromisoformat(booking_date_str)
                    if existing_exam.scheduled_date != new_date:
                        existing_exam.scheduled_date = new_date
                except ValueError:
                    pass
            # Also backfill city and fix name for existing patients
            patient_data_ex = b.get("patient") or {}
            pn_ex = patient_data_ex.get("personalNumber", "")
            if pn_ex:
                p_ex = await db.execute(select(Patient).where(Patient.personnummer == pn_ex))
                pat_ex = p_ex.scalars().first()
                if pat_ex:
                    # Fix name if it was a placeholder
                    first_name_ex = patient_data_ex.get("firstName", "")
                    last_name_ex = patient_data_ex.get("lastName", "")
                    if pat_ex.first_name == "Manuell" or pat_ex.last_name == "Bokning":
                        if first_name_ex and last_name_ex:
                            pat_ex.first_name = first_name_ex
                            pat_ex.last_name = last_name_ex
                            
                    # Fetch city from Webdoc if missing
                    if not pat_ex.city:
                        try:
                            details = await webdoc_client.fetch_patient_details(pn_ex)
                            if details.get("city"):
                                pat_ex.city = details["city"]
                        except Exception:
                            pass
            continue
        
        patient_data = b.get("patient")
        if not patient_data:
            continue
        pn = patient_data.get("personalNumber", "")
        if not pn:
            continue
        
        first_name = patient_data.get("firstName", "")
        last_name = patient_data.get("lastName", "")
        
        p_result = await db.execute(select(Patient).where(Patient.personnummer == pn))
        patient = p_result.scalars().first()
        if not patient:
            patient = Patient(
                personnummer=pn,
                first_name=first_name,
                last_name=last_name,
                webdoc_patient_id=str(patient_data.get("id", ""))
            )
            db.add(patient)
            await db.flush()
        
        # Fetch city/postort from Webdoc if not already set
        if not patient.city:
            try:
                details = await webdoc_client.fetch_patient_details(pn)
                if details.get("city"):
                    patient.city = details["city"]
            except Exception:
                pass  # Non-critical, skip silently
        
        assigned_device = None
        new_duration = {"24h": 1, "48h": 2, "72h": 3}.get(exam_type.value, 1)
        for dev in all_devices:
            if booking_date_str:
                try:
                    b_date = date.fromisoformat(booking_date_str)
                except ValueError:
                    b_date = None
                if b_date:
                    new_end = b_date + timedelta(days=new_duration)
                    # Check for any overlapping exam on this device
                    conflict_result = await db.execute(
                        select(Exam).where(
                            Exam.device_id == dev.id,
                            Exam.status.in_([ExamStatus.SCHEDULED, ExamStatus.ACTIVE])
                        )
                    )
                    has_conflict = False
                    for existing in conflict_result.scalars().all():
                        e_dur = get_effective_duration(existing)
                        
                        if existing.status == ExamStatus.ACTIVE:
                            # Active exam — use expected_return_at if set,
                            # otherwise use started_at + duration as estimate
                            if existing.expected_return_at:
                                e_end = existing.expected_return_at
                                if isinstance(e_end, datetime):
                                    e_end = e_end.date()
                            elif existing.started_at:
                                e_end = existing.started_at.date() + timedelta(days=e_dur)
                            else:
                                # Active but no dates — assume conflict
                                has_conflict = True
                                break
                            # Device is free if expected back before new booking starts
                            if e_end <= b_date:
                                continue  # No conflict — device will be back in time
                            else:
                                has_conflict = True
                                break
                        else:
                            # Scheduled exam — use scheduled_date + duration
                            if existing.scheduled_date:
                                e_start = existing.scheduled_date
                                e_end = e_start + timedelta(days=e_dur)
                                # Check date range overlap
                                if e_start < new_end and b_date < e_end:
                                    has_conflict = True
                                    break
                    if has_conflict:
                        continue
            assigned_device = dev
            break
        
        if not assigned_device and all_devices:
            assigned_device = all_devices[0]
        
        if not assigned_device:
            continue
        
        try:
            sched_date = date.fromisoformat(booking_date_str) if booking_date_str else date.today()
        except ValueError:
            sched_date = date.today()
        
        new_exam = Exam(
            device_id=assigned_device.id,
            patient_id=patient.id,
            exam_type=exam_type,
            return_type=ReturnType.POSTAL if exam_type == ExamType.H72 else ReturnType.CLINIC,
            status=ExamStatus.SCHEDULED,
            scheduled_date=sched_date,
            start_time=booking_start_time or None,
            atgardskod=ATGARDSKOD_MAP.get(exam_type, "E1005"),
            webdoc_booking_id=booking_id,
        )
        db.add(new_exam)
        new_count += 1
    
    await db.commit()
    
    return {
        "message": f"Webdoc sync complete! {new_count} new, {cancel_count} cancelled.",
        "new": new_count,
        "cancelled": cancel_count,
    }
