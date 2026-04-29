import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Date, ForeignKey, Boolean, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .database import Base

class DeviceStatus(str, enum.Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    ON_PATIENT = "on_patient"
    IN_TRANSIT = "in_transit"
    RETURNED = "returned"
    PROCESSING = "processing"
    MAINTENANCE = "maintenance"
    LOST = "lost"

class ChainType(str, enum.Enum):
    WORKHORSE = "workhorse"
    POSTAL_72H = "postal_72h"
    PURE_POSTAL = "pure_postal"

class ExamType(str, enum.Enum):
    H24 = "24h"
    H48 = "48h"
    H72 = "72h"

class ReturnType(str, enum.Enum):
    CLINIC = "clinic"
    POSTAL = "postal"

class ExamStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Device(Base):
    __tablename__ = "devices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_code = Column(String(10), unique=True, index=True)
    serial_number = Column(String(50))
    model = Column(String(50))
    status = Column(Enum(DeviceStatus), default=DeviceStatus.AVAILABLE)
    chain_type = Column(Enum(ChainType), nullable=True)
    chain_position = Column(Integer, nullable=True)
    purchased_at = Column(DateTime, nullable=True)
    last_maintenance_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    exams = relationship("Exam", back_populates="device")
    events = relationship("DeviceEvent", back_populates="device")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    personnummer = Column(String(13), unique=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)  # Postort from Webdoc
    webdoc_patient_id = Column(String(50), nullable=True)
    is_postal = Column(Boolean, default=False)

    exams = relationship("Exam", back_populates="patient")

class Exam(Base):
    __tablename__ = "exams"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"))
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"))
    exam_type = Column(Enum(ExamType))
    atgardskod = Column(String(10)) # E1005, E1006, E1007
    price_sek = Column(Integer)
    return_type = Column(Enum(ReturnType))
    status = Column(Enum(ExamStatus), default=ExamStatus.SCHEDULED)
    
    scheduled_date = Column(Date)
    started_at = Column(DateTime, nullable=True)
    expected_removal_at = Column(DateTime, nullable=True)
    actual_removal_at = Column(DateTime, nullable=True)
    expected_return_at = Column(DateTime, nullable=True)
    actual_return_at = Column(DateTime, nullable=True)
    
    webdoc_booking_id = Column(String(50), nullable=True)
    webdoc_remiss_id = Column(String(50), nullable=True)
    remissvar_sent = Column(Boolean, default=False)
    referring_physician = Column(String(100), nullable=True)
    clinical_indication = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    start_time = Column(String(10), nullable=True)  # e.g. "08:30" from Webdoc
    duration_days = Column(Integer, nullable=True)  # Custom override: 1-7 days. Null = use exam_type default

    device = relationship("Device", back_populates="exams")
    patient = relationship("Patient", back_populates="exams")
    events = relationship("DeviceEvent", back_populates="exam")

class DeviceEvent(Base):
    __tablename__ = "device_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"))
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id"), nullable=True)
    
    event_type = Column(String(30))
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=True)
    triggered_by = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata_ = Column("metadata", JSONB, nullable=True) # avoiding overlapping with Base.metadata

    device = relationship("Device", back_populates="events")
    exam = relationship("Exam", back_populates="events")
