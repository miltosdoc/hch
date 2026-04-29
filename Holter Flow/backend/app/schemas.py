from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime, date
from .models import DeviceStatus, ChainType, ExamType, ReturnType, ExamStatus

# Devices
class DeviceBase(BaseModel):
    device_code: str
    serial_number: Optional[str] = None
    model: Optional[str] = None
    status: DeviceStatus = DeviceStatus.AVAILABLE
    chain_type: Optional[ChainType] = None
    chain_position: Optional[int] = None
    purchased_at: Optional[datetime] = None
    last_maintenance_at: Optional[datetime] = None
    notes: Optional[str] = None

class DeviceCreate(DeviceBase):
    pass

class DeviceResponse(DeviceBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

# Patients
class PatientBase(BaseModel):
    personnummer: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    webdoc_patient_id: Optional[str] = None
    is_postal: bool = False

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

# Exams
class ExamBase(BaseModel):
    device_id: UUID
    patient_id: UUID
    exam_type: ExamType
    atgardskod: str
    price_sek: int
    return_type: ReturnType
    status: ExamStatus = ExamStatus.SCHEDULED
    scheduled_date: date
    started_at: Optional[datetime] = None
    expected_removal_at: Optional[datetime] = None
    actual_removal_at: Optional[datetime] = None
    expected_return_at: Optional[datetime] = None
    actual_return_at: Optional[datetime] = None
    webdoc_booking_id: Optional[str] = None
    webdoc_remiss_id: Optional[str] = None
    remissvar_sent: bool = False
    referring_physician: Optional[str] = None
    clinical_indication: Optional[str] = None
    notes: Optional[str] = None

class ExamCreate(ExamBase):
    pass

class ExamResponse(ExamBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

# Device Events
class DeviceEventBase(BaseModel):
    device_id: UUID
    exam_id: Optional[UUID] = None
    event_type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    triggered_by: Optional[str] = None
    metadata_: Optional[Any] = None

class DeviceEventCreate(DeviceEventBase):
    pass

class DeviceEventResponse(DeviceEventBase):
    id: UUID
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)
