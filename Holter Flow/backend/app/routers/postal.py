from fastapi import APIRouter, Depends, HTTPException, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Dict, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime, date, timedelta

from ..database import get_db
from ..models import Exam, ExamStatus, ExamType, ReturnType, Patient, Device, DeviceStatus, DeviceEvent

router = APIRouter()


def calculate_business_days_ahead(start_date: date, business_days: int) -> date:
    """Add business_days to start_date, skipping weekends."""
    current = start_date
    added = 0
    while added < business_days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri
            added += 1
    return current


def get_exam_duration_days(exam_type) -> int:
    if exam_type == ExamType.H24:
        return 1
    elif exam_type == ExamType.H48:
        return 2
    return 3


@router.get("/active")
async def get_active_postal(db: AsyncSession = Depends(get_db)):
    """Retrieve all active exams where the device was sent via postal service."""
    result = await db.execute(
        select(Exam, Patient, Device)
        .join(Patient, Exam.patient_id == Patient.id)
        .join(Device, Exam.device_id == Device.id)
        .where(Exam.return_type == ReturnType.POSTAL)
        .where(Exam.status.in_([ExamStatus.SCHEDULED, ExamStatus.ACTIVE]))
    )
    rows = result.all()
    
    formatted = []
    for exam, patient, device in rows:
        # Smart estimated arrival: duration + 3 business days postal transit
        duration_days = get_exam_duration_days(exam.exam_type)
        postal_days = 3  # Will be replaced by live median later
        
        if exam.scheduled_date:
            # Patient wears device for duration_days, then mails back
            removal_date = exam.scheduled_date + timedelta(days=duration_days)
            estimated_arrival = calculate_business_days_ahead(removal_date, postal_days)
        else:
            estimated_arrival = None
        
        # Calculate actual transit days if in transit
        days_in_transit = 0
        if exam.started_at:
            days_in_transit = (datetime.utcnow() - exam.started_at).days
        
        formatted.append({
            "exam_id": str(exam.id),
            "device_id": str(device.id),
            "device_code": device.device_code,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_pn": patient.personnummer,
            "exam_type": exam.exam_type.value if exam.exam_type else None,
            "device_status": device.status.value if device.status else None,
            "scheduled_date": exam.scheduled_date.isoformat() if exam.scheduled_date else None,
            "start_time": exam.start_time,
            "started_at": exam.started_at.isoformat() if exam.started_at else None,
            "expected_return_at": exam.expected_return_at.isoformat() if exam.expected_return_at else None,
            "estimated_arrival": estimated_arrival.isoformat() if estimated_arrival else None,
            "days_in_transit": days_in_transit,
            "actual_return_at": exam.actual_return_at.isoformat() if exam.actual_return_at else None,
        })
    return formatted


@router.get("/statistics")
async def get_postal_statistics(db: AsyncSession = Depends(get_db)):
    """
    Calculate postal transit statistics from completed postal exams.
    Returns median transit time so we can dynamically adjust estimates.
    """
    result = await db.execute(
        select(Exam)
        .where(Exam.return_type == ReturnType.POSTAL)
        .where(Exam.status == ExamStatus.COMPLETED)
        .where(Exam.started_at.isnot(None))
        .where(Exam.actual_return_at.isnot(None))
    )
    completed = result.scalars().all()
    
    if not completed:
        return {
            "total_completed": 0,
            "median_transit_days": 3,  # Default assumption
            "avg_transit_days": 3.0,
            "min_days": None,
            "max_days": None,
            "transit_times": [],
        }
    
    transit_times = []
    for ex in completed:
        days = (ex.actual_return_at - ex.started_at).days
        if days >= 0:
            transit_times.append(days)
    
    transit_times.sort()
    
    n = len(transit_times)
    if n == 0:
        median = 3
    elif n % 2 == 1:
        median = transit_times[n // 2]
    else:
        median = (transit_times[n // 2 - 1] + transit_times[n // 2]) / 2
    
    return {
        "total_completed": n,
        "median_transit_days": round(median, 1),
        "avg_transit_days": round(sum(transit_times) / n, 1) if n > 0 else 3.0,
        "min_days": min(transit_times) if transit_times else None,
        "max_days": max(transit_times) if transit_times else None,
        "transit_times": transit_times[-20:],  # Last 20 for sparkline
    }


@router.post("/{exam_id}/transit")
async def mark_in_transit(exam_id: str, db: AsyncSession = Depends(get_db)):
    """Marks a postal device as IN_TRANSIT (mailed to patient or mailed back)."""
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    dev_result = await db.execute(select(Device).where(Device.id == exam.device_id))
    device = dev_result.scalar_one_or_none()
    
    old_status = device.status
    device.status = DeviceStatus.IN_TRANSIT
    exam.status = ExamStatus.ACTIVE
    if not exam.started_at:
        exam.started_at = datetime.utcnow()
        
    event = DeviceEvent(
        device_id=device.id,
        exam_id=exam.id,
        event_type="status_change",
        from_status=old_status,
        to_status=DeviceStatus.IN_TRANSIT,
        triggered_by="postal_system",
        metadata_={"note": "Marked as In Transit"}
    )
    db.add(event)
    await db.commit()
    return {"message": "Device marked in transit", "device_code": device.device_code}


@router.post("/{exam_id}/receive")
async def mark_received(exam_id: str, db: AsyncSession = Depends(get_db)):
    """Marks a postal device as securely received back at the clinic."""
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    dev_result = await db.execute(select(Device).where(Device.id == exam.device_id))
    device = dev_result.scalar_one_or_none()
    
    old_status = device.status
    device.status = DeviceStatus.AVAILABLE
    exam.status = ExamStatus.COMPLETED
    exam.actual_return_at = datetime.utcnow()
    
    event = DeviceEvent(
        device_id=device.id,
        exam_id=exam.id,
        event_type="status_change",
        from_status=old_status,
        to_status=DeviceStatus.AVAILABLE,
        triggered_by="postal_system",
        metadata_={"note": "Device received by clinic"}
    )
    db.add(event)
    await db.commit()
    return {"message": "Device received and marked Available", "device_code": device.device_code}
