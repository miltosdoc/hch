from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel

from ..models import Device, DeviceEvent, DeviceStatus, ChainType, Patient, Exam, ExamStatus, ExamType, ReturnType
from ..schemas import PatientCreate, ExamCreate
from fastapi import HTTPException

# Schemas for the service requests to separate concerns
class CheckoutRequest(BaseModel):
    patient: PatientCreate
    exam_type: ExamType
    return_type: ReturnType
    expected_removal_at: datetime

class DeviceService:
    @staticmethod
    async def log_event(db: AsyncSession, device_id: UUID, event_type: str, from_status: str, to_status: str, triggered_by: str = "system", metadata: dict = None, exam_id: UUID = None):
        event = DeviceEvent(
            device_id=device_id,
            exam_id=exam_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            triggered_by=triggered_by,
            metadata_=metadata
        )
        db.add(event)

    @staticmethod
    async def get_device(db: AsyncSession, device_id: UUID) -> Device:
        result = await db.execute(select(Device).where(Device.id == device_id))
        device = result.scalars().first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        return device

    @staticmethod
    async def get_all_devices(db: AsyncSession):
        result = await db.execute(select(Device))
        return result.scalars().all()

    @staticmethod
    async def create_device(db: AsyncSession, device_code: str, serial_number: str = None, chain_type: str = None) -> Device:
        """Adds a brand new physical device to the active tracking system."""
        ct = None
        if chain_type:
            try:
                ct = ChainType(chain_type)
            except ValueError:
                ct = None
        
        device = Device(
            device_code=device_code,
            serial_number=serial_number,
            chain_type=ct,
            status=DeviceStatus.AVAILABLE
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
        return device

    @staticmethod
    async def delete_device(db: AsyncSession, device_id: UUID) -> bool:
        """Removes a physical device from tracking (e.g., permanently broken)."""
        device = await DeviceService.get_device(db, device_id)
        await db.delete(device)
        await db.commit()
        return True

    @staticmethod
    async def get_fleet_status(db: AsyncSession):
        result = await db.execute(
            select(Device.status, func.count(Device.id)).group_by(Device.status)
        )
        counts = {status.value: 0 for status in DeviceStatus}
        for status, count in result:
            counts[status.value] = count
        return counts

    @staticmethod
    async def get_fleet_status_full(db: AsyncSession):
        """Returns both a counts summary and the full device list for the frontend."""
        result = await db.execute(select(Device).order_by(Device.device_code))
        devices = result.scalars().all()

        counts = {status.value: 0 for status in DeviceStatus}
        device_list = []
        for d in devices:
            counts[d.status.value] += 1
            device_list.append({
                "id": str(d.id),
                "device_code": d.device_code,
                "status": d.status.value,
                "chain_type": d.chain_type.value if d.chain_type else None,
                "serial_number": d.serial_number,
                "model": d.model,
                "notes": d.notes,
            })

        return {"counts": counts, "devices": device_list}

    @staticmethod
    async def update_device_status(db: AsyncSession, device_id: UUID, new_status: DeviceStatus, user: str = "system"):
        device = await DeviceService.get_device(db, device_id)
        from_status = device.status
        device.status = new_status
        await DeviceService.log_event(db, device.id, "STATUS_CHANGE", from_status, new_status, triggered_by=user)
        await db.commit()
        await db.refresh(device)
        return device

    @staticmethod
    async def get_or_create_patient(db: AsyncSession, patient_data: PatientCreate) -> Patient:
        result = await db.execute(select(Patient).where(Patient.personnummer == patient_data.personnummer))
        patient = result.scalars().first()
        if not patient:
            # Create new patient
            patient = Patient(**patient_data.model_dump())
            db.add(patient)
            await db.flush() # flush to get the patient ID
        return patient

    @staticmethod
    async def checkout_device(db: AsyncSession, device_id: UUID, checkout_data: CheckoutRequest, user: str = "system"):
        device = await DeviceService.get_device(db, device_id)
        
        if device.status not in (DeviceStatus.AVAILABLE, DeviceStatus.RETURNED):
            raise HTTPException(status_code=400, detail=f"Device cannot be checked out from state {device.status}")

        # 1. Get or create the patient record
        patient = await DeviceService.get_or_create_patient(db, checkout_data.patient)

        # 2. Determine price and atgardskod based on PRD logic
        prices = {ExamType.H24: 2582, ExamType.H48: 3057, ExamType.H72: 3522}
        atgardskods = {ExamType.H24: "E1005", ExamType.H48: "E1006", ExamType.H72: "E1007"}

        # 3. Calculate return timeframe based on postal vs clinic
        expected_return = checkout_data.expected_removal_at
        if checkout_data.return_type == ReturnType.POSTAL:
            # Add 3 days for postal transit per PRD logic
            expected_return += timedelta(days=3)

        # 4. Create Exam record
        # Note: Webdoc booking API call would be triggered here asynchronously
        exam = Exam(
            device_id=device.id,
            patient_id=patient.id,
            exam_type=checkout_data.exam_type,
            atgardskod=atgardskods[checkout_data.exam_type],
            price_sek=prices[checkout_data.exam_type],
            return_type=checkout_data.return_type,
            status=ExamStatus.ACTIVE,
            scheduled_date=datetime.utcnow().date(),
            started_at=datetime.utcnow(),
            expected_removal_at=checkout_data.expected_removal_at,
            expected_return_at=expected_return
        )
        db.add(exam)
        await db.flush()

        # 5. Transition device state
        from_status = device.status
        device.status = DeviceStatus.ON_PATIENT
        
        # Log event
        await DeviceService.log_event(
            db, 
            device.id, 
            "CHECKOUT", 
            from_status, 
            DeviceStatus.ON_PATIENT, 
            triggered_by=user, 
            exam_id=exam.id
        )

        await db.commit()
        await db.refresh(device)
        return device, exam

    @staticmethod
    async def checkin_device(db: AsyncSession, device_id: UUID, user: str = "system"):
        device = await DeviceService.get_device(db, device_id)
        
        if device.status not in (DeviceStatus.ON_PATIENT, DeviceStatus.IN_TRANSIT, DeviceStatus.LOST):
            raise HTTPException(status_code=400, detail=f"Device cannot be checked in from state {device.status}")

        # Finalize exam
        result = await db.execute(select(Exam).where(Exam.device_id == device.id).where(Exam.status == ExamStatus.ACTIVE))
        active_exam = result.scalars().first()
        
        if active_exam:
            active_exam.status = ExamStatus.COMPLETED
            active_exam.actual_return_at = datetime.utcnow()

        # Transition device
        from_status = device.status
        device.status = DeviceStatus.RETURNED
        
        exam_id = active_exam.id if active_exam else None

        await DeviceService.log_event(
            db, 
            device.id, 
            "CHECKIN", 
            from_status, 
            DeviceStatus.RETURNED, 
            triggered_by=user,
            exam_id=exam_id
        )

        await db.commit()
        await db.refresh(device)
        return device
