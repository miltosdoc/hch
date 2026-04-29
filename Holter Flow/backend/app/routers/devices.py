from fastapi import APIRouter, Depends, HTTPException, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID

from ..database import get_db
from ..schemas import DeviceResponse, DeviceEventResponse
from ..models import DeviceStatus
from ..services.device_service import DeviceService, CheckoutRequest

router = APIRouter()

@router.get("", response_model=List[DeviceResponse])
async def get_devices(db: AsyncSession = Depends(get_db)):
    """List all devices with current status."""
    return await DeviceService.get_all_devices(db)

@router.get("/fleet-status")
async def get_fleet_status(db: AsyncSession = Depends(get_db)):
    """Fleet overview: returns counts by status AND full device list."""
    return await DeviceService.get_fleet_status_full(db)

from pydantic import BaseModel
from typing import Optional

class CreateDeviceRequest(BaseModel):
    device_code: str
    serial_number: Optional[str] = None
    chain_type: Optional[str] = None  # "workhorse", "postal_72h", "pure_postal"

@router.post("/create", response_model=DeviceResponse)
async def create_device(
    body: CreateDeviceRequest,
    db: AsyncSession = Depends(get_db)
):
    """Dynamically register a new device to the fleet."""
    return await DeviceService.create_device(
        db, body.device_code, 
        serial_number=body.serial_number,
        chain_type=body.chain_type
    )

@router.delete("/{id}")
async def delete_device(id: UUID = Path(...), db: AsyncSession = Depends(get_db)):
    """Permanently remove a device."""
    await DeviceService.delete_device(db, id)
    return {"message": f"Device {id} deleted."}

@router.get("/{id}", response_model=DeviceResponse)
async def get_device(id: UUID = Path(...), db: AsyncSession = Depends(get_db)):
    """Device detail including history."""
    return await DeviceService.get_device(db, id)

@router.post("/{id}/checkout", response_model=DeviceResponse)
async def checkout_device(
    id: UUID = Path(...),
    checkout_data: CheckoutRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Assign device to patient, start exam, and trigger Webdoc Booking."""
    # Webdoc booking is conceptually triggered inside checkout_device
    device, exam = await DeviceService.checkout_device(db, id, checkout_data)
    return device

@router.post("/{id}/checkin", response_model=DeviceResponse)
async def checkin_device(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """Mark device returned, finalizing its current exam."""
    return await DeviceService.checkin_device(db, id)

@router.post("/{id}/status", response_model=DeviceResponse)
async def update_device_status(
    id: UUID = Path(...),
    new_status: DeviceStatus = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """Manual status transition (e.g., to MAINTENANCE or LOST)."""
    return await DeviceService.update_device_status(db, id, new_status)


class EditDeviceRequest(BaseModel):
    device_code: Optional[str] = None
    serial_number: Optional[str] = None
    chain_type: Optional[str] = None  # "workhorse", "postal_72h", "pure_postal", or null to clear

from ..models import ChainType, Device
from sqlalchemy.future import select

@router.patch("/{id}")
async def edit_device(
    id: UUID = Path(...),
    body: EditDeviceRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Edit device properties: code, serial number, chain type."""
    result = await db.execute(select(Device).where(Device.id == id))
    device = result.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if body.device_code is not None:
        device.device_code = body.device_code
    if body.serial_number is not None:
        device.serial_number = body.serial_number if body.serial_number else None
    if body.chain_type is not None:
        if body.chain_type == "":
            device.chain_type = None
        else:
            try:
                device.chain_type = ChainType(body.chain_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid chain_type: {body.chain_type}")
    
    await db.commit()
    await db.refresh(device)
    return {
        "message": f"Device {device.device_code} updated",
        "id": str(device.id),
        "device_code": device.device_code,
        "serial_number": device.serial_number,
        "chain_type": device.chain_type.value if device.chain_type else None,
    }

