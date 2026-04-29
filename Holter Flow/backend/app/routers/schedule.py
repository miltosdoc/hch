from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from ..database import get_db
from ..services.scheduling_service import SchedulingService
from ..models import ExamType, ReturnType

router = APIRouter()

import json
from pathlib import Path

def get_tidsramar():
    try:
        path = Path("data/settings.json")
        if path.exists():
            with open(path, "r") as f:
                data = json.load(f)
                return data.get("tidsramar", ["08:00", "08:30", "13:00"])
    except:
        pass
    return ["08:00", "08:30", "13:00"]

@router.get("/optimal-slots")
async def optimal_slots(
    exam_type: str,
    target_date: date,
    db: AsyncSession = Depends(get_db)
):
    """
    Get optimal available slots across a 7-day period.
    exam_type expected as '24h', '48h', '72h'
    """
    from ..models import ExamType, ReturnType
    
    e_type = ExamType.H24
    if exam_type == '48h': e_type = ExamType.H48
    elif exam_type == '72h': e_type = ExamType.H72
        
    # By default, 24h/48h are CLINIC, 72h is typically POSTAL. 
    # For now, we assume standard returns unless postal.
    r_type = ReturnType.POSTAL if e_type == ExamType.H72 else ReturnType.CLINIC
    
    allowed_times = get_tidsramar()
    
    slots = await SchedulingService.calculate_weekly_slots(
        db, 
        exam_type=e_type, 
        return_type=r_type, 
        start_date=target_date,
        allowed_times=allowed_times
    )
    return slots

@router.post("/settings/tidsramar")
async def update_tidsramar(times: list[str]):
    path = Path("data/settings.json")
    path.parent.mkdir(exist_ok=True)
    data = {}
    if path.exists():
        with open(path, "r") as f:
            data = json.load(f)
            
    data["tidsramar"] = times
    with open(path, "w") as f:
        json.dump(data, f)
    return {"message": "Tidsramar updated", "tidsramar": times}
    
@router.get("/settings/tidsramar")
async def fetch_tidsramar():
    return get_tidsramar()

@router.get("/capacity")
async def get_capacity(db: AsyncSession = Depends(get_db)):
    """
    Current week capacity and utilization.
    """
    return await SchedulingService.get_capacity(db)

@router.post("/rebalance")
async def rebalance_chains(db: AsyncSession = Depends(get_db)):
    """
    Re-optimize chain assignments ensuring formatting maps purely to PRD (19 / 1 / 3).
    """
    counts = await SchedulingService.rebalance_chains(db)
    return {"message": "Rebalance successful", "assigned_counts": counts}

@router.get("/revenue-suggestions")
async def revenue_suggestions(db: AsyncSession = Depends(get_db)):
    """
    Calculates empty device slots for the current week and suggests optimal
    bookings ordered by revenue potential.
    """
    from ..models import Device, Exam, ExamStatus, ExamType
    from sqlalchemy.future import select
    from datetime import timedelta
    
    PRICES = {"24h": 2582, "48h": 3057, "72h": 3522}
    
    today = date.today()
    # Get the current week's Monday
    day_of_week = today.weekday()
    monday = today - timedelta(days=day_of_week)
    
    allowed_times = get_tidsramar()
    
    # Get all devices and current exams
    dev_res = await db.execute(select(Device))
    devices = dev_res.scalars().all()
    
    ex_res = await db.execute(
        select(Exam).where(Exam.status.in_([ExamStatus.SCHEDULED, ExamStatus.ACTIVE]))
    )
    active_exams = ex_res.scalars().all()
    
    # Build occupied slots: device_id -> set of dates
    occupied = {}
    for ex in active_exams:
        if ex.device_id and ex.scheduled_date:
            if ex.device_id not in occupied:
                occupied[ex.device_id] = set()
            dur = 1 if ex.exam_type == ExamType.H24 else 2 if ex.exam_type == ExamType.H48 else 3
            for d_off in range(dur + 1):
                occupied[ex.device_id].add(ex.scheduled_date + timedelta(days=d_off))
    
    suggestions = []
    
    # Check each weekday this week
    for day_offset in range(5):  # Mon-Fri
        check_date = monday + timedelta(days=day_offset)
        if check_date < today:
            continue  # Skip past days
        
        # Count available devices on this date
        available_devices = []
        for dev in devices:
            dev_occupied = occupied.get(dev.id, set())
            if check_date not in dev_occupied:
                available_devices.append(dev)
        
        if not available_devices:
            continue
        
        # Suggest filling with highest revenue first (72h > 48h > 24h)
        for exam_label, price in sorted(PRICES.items(), key=lambda x: -x[1]):
            dur = int(exam_label.replace("h", ""))
            # Check if device is free for full duration
            for dev in available_devices[:3]:  # Max 3 suggestions per exam type per day
                all_free = True
                dev_occ = occupied.get(dev.id, set())
                for d_off in range(dur + 1):
                    if (check_date + timedelta(days=d_off)) in dev_occ:
                        all_free = False
                        break
                if all_free:
                    suggestions.append({
                        "date": check_date.isoformat(),
                        "time": allowed_times[0] if allowed_times else "08:00",
                        "exam_type": exam_label,
                        "device_code": dev.device_code,
                        "device_id": str(dev.id),
                        "revenue_sek": price,
                        "available_devices": len(available_devices),
                    })
                    break  # One suggestion per exam type per day
    
    # Sort by revenue descending
    suggestions.sort(key=lambda s: -s["revenue_sek"])
    
    total_potential = sum(s["revenue_sek"] for s in suggestions)
    
    return {
        "suggestions": suggestions[:15],
        "total_potential_sek": total_potential,
        "empty_slots_count": len(suggestions),
    }
