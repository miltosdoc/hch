from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models import Device, DeviceStatus, ChainType, ExamType, ReturnType, Exam, ExamStatus


def _effective_duration(exam) -> int:
    """Get effective duration in days, considering custom overrides."""
    if exam.duration_days:
        return exam.duration_days
    return {"24h": 1, "48h": 2, "72h": 3}.get(
        exam.exam_type.value if exam.exam_type else "24h", 1
    )


class SchedulingService:
    @staticmethod
    async def rebalance_chains(db: AsyncSession):
        """
        Enforces the mathematical ratio across all devices:
        - 19 Workhorse
        - 1 Postal 72h
        - 3 Pure Postal
        """
        result = await db.execute(select(Device).order_by(Device.device_code))
        devices = result.scalars().all()
        
        counts = {
            ChainType.WORKHORSE: 19,
            ChainType.POSTAL_72H: 1,
            ChainType.PURE_POSTAL: 3
        }
        
        assigned = {
            ChainType.WORKHORSE: 0,
            ChainType.POSTAL_72H: 0,
            ChainType.PURE_POSTAL: 0
        }

        for device in devices:
            if device.chain_type and assigned[device.chain_type] < counts[device.chain_type]:
                assigned[device.chain_type] += 1
            else:
                for req_type, max_c in counts.items():
                    if assigned[req_type] < max_c:
                        device.chain_type = req_type
                        assigned[req_type] += 1
                        break
        
        await db.commit()
        return dict(assigned)

    @staticmethod
    async def calculate_weekly_slots(
        db: AsyncSession, 
        exam_type: ExamType, 
        return_type: ReturnType, 
        start_date: date,
        allowed_times: List[str] = ["08:00", "08:30", "13:00"]
    ):
        """
        Calculates optimal booking slots across a 7-day period.
        Time-aware: skips past dates and past times on today.
        Uses expected_return_at for active exams.
        """
        duration_days = {"24h": 1, "48h": 2, "72h": 3}.get(exam_type.value, 1)
        now = datetime.now(ZoneInfo("Europe/Stockholm"))
        today = now.date()
        current_time_str = now.strftime("%H:%M")
        
        # Always start from today — never suggest past dates regardless of what frontend sends
        effective_start = max(start_date, today)
        
        # Weekends are allowed — clinic places Holter devices any day
        
        # Determine optimal chain 
        optimal_chain_type = ChainType.WORKHORSE
        if exam_type == ExamType.H72:
            optimal_chain_type = ChainType.POSTAL_72H
        elif return_type == ReturnType.POSTAL:
            optimal_chain_type = ChainType.PURE_POSTAL

        res = await db.execute(select(Device))
        devices = res.scalars().all()
        
        if not devices:
            return []

        # Get all active/scheduled exams
        ex_res = await db.execute(
            select(Exam).where(
                Exam.status.in_([ExamStatus.SCHEDULED, ExamStatus.ACTIVE])
            )
        )
        active_exams = ex_res.scalars().all()
        
        # Build device busy ranges: device_id -> [(start, end), ...]
        device_schedules = {d.id: [] for d in devices}
        for ex in active_exams:
            if not ex.device_id:
                continue
                
            ex_dur = _effective_duration(ex)
            
            if ex.status == ExamStatus.ACTIVE:
                # Active exam: device is busy until expected_return_at (or estimate)
                if ex.expected_return_at:
                    busy_end = ex.expected_return_at
                    if isinstance(busy_end, datetime):
                        busy_end = busy_end.date()
                elif ex.started_at:
                    busy_end = ex.started_at.date() + timedelta(days=ex_dur)
                else:
                    busy_end = today + timedelta(days=ex_dur)
                
                busy_start = ex.started_at.date() if ex.started_at else (ex.scheduled_date or today)
                device_schedules[ex.device_id].append((busy_start, busy_end))
            else:
                # Scheduled exam: busy from scheduled_date to scheduled_date + duration
                if ex.scheduled_date:
                    busy_start = ex.scheduled_date
                    busy_end = busy_start + timedelta(days=ex_dur)
                    device_schedules[ex.device_id].append((busy_start, busy_end))

        available_slots = []
        business_days_found = 0
        max_business_days = 7

        # --- Ad-hoc "Nu" slot: if any device is free RIGHT NOW, offer it ---
        now_time_str = now.strftime("%H:%M")
        needed_end_today = today + timedelta(days=duration_days)
        
        # Find a device available right now
        now_device = None
        now_is_optimal = False
        for device in devices:
            if device.chain_type == optimal_chain_type:
                conflict = False
                for (b_start, b_end) in device_schedules[device.id]:
                    if not (needed_end_today <= b_start or today >= b_end):
                        conflict = True
                        break
                if not conflict:
                    now_device = device
                    now_is_optimal = True
                    break
        if not now_device:
            for device in devices:
                conflict = False
                for (b_start, b_end) in device_schedules[device.id]:
                    if not (needed_end_today <= b_start or today >= b_end):
                        conflict = True
                        break
                if not conflict:
                    now_device = device
                    now_is_optimal = False
                    break
        
        if now_device:
            available_slots.append({
                "date": today.isoformat(),
                "time": now_time_str,
                "device_id": str(now_device.id),
                "device_code": now_device.device_code,
                "optimal_match": now_is_optimal,
                "expected_return_at": (today + timedelta(days=duration_days)).isoformat(),
                "warning": None if now_is_optimal else f"Breaks chain constraint: Assigned to {now_device.chain_type}",
                "is_now": True
            })

        # --- Scheduled time slots for the next 7 days ---
        # Scan up to 21 calendar days to find 7 days
        for day_offset in range(21):
            if business_days_found >= max_business_days:
                break
                
            current_date = effective_start + timedelta(days=day_offset)
            
            business_days_found += 1
                
            needed_end_date = current_date + timedelta(days=duration_days)
            
            # Find best device for this day — try ALL devices, not just first match
            selected_device = None
            is_optimal = False
            
            # Try optimal chain match first
            for device in devices:
                if device.chain_type == optimal_chain_type:
                    conflict = False
                    for (b_start, b_end) in device_schedules[device.id]:
                        # Overlap check: NOT (new_end <= busy_start OR new_start >= busy_end)
                        if not (needed_end_date <= b_start or current_date >= b_end):
                            conflict = True
                            break
                    if not conflict:
                        selected_device = device
                        is_optimal = True
                        break
            
            # Fallback: any available device
            if not selected_device:
                for device in devices:
                    conflict = False
                    for (b_start, b_end) in device_schedules[device.id]:
                        if not (needed_end_date <= b_start or current_date >= b_end):
                            conflict = True
                            break
                    if not conflict:
                        selected_device = device
                        is_optimal = False
                        break
            
            if selected_device:
                for t in allowed_times:
                    # Skip past times on today
                    if current_date == today and t <= current_time_str:
                        continue
                    
                    available_slots.append({
                        "date": current_date.isoformat(),
                        "time": t,
                        "device_id": str(selected_device.id),
                        "device_code": selected_device.device_code,
                        "optimal_match": is_optimal,
                        "expected_return_at": (current_date + timedelta(days=duration_days)).isoformat(),
                        "warning": None if is_optimal else f"Breaks chain constraint: Assigned to {selected_device.chain_type}"
                    })
                    
        return available_slots

    @staticmethod
    async def get_capacity(db: AsyncSession):
        """Calculates current utilization vs capacity."""
        res_dev = await db.execute(select(Device))
        total_devices = len(res_dev.scalars().all())
        
        res_exm = await db.execute(select(Exam).where(Exam.status == ExamStatus.ACTIVE))
        active_exams = len(res_exm.scalars().all())
        
        capacity_filled = (active_exams / total_devices) * 100 if total_devices > 0 else 0
        
        return {
            "total_devices": total_devices,
            "active_exams": active_exams,
            "utilization_percent": round(capacity_filled, 1)
        }
