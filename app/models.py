from pydantic import BaseModel
from typing import Optional

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: Optional[str] = None
    location: Optional[str] = None
    owner_name: str
    owner_phone: str
    event_type: Optional[str] = None
    package_type: Optional[str] = "basic"

class GuestCreate(BaseModel):
    event_id: str
    name: str
    phone: str

class RSVPUpdate(BaseModel):
    guest_id: str
    status: str

class GateKeeperCreate(BaseModel):
    event_id: str
    name: str
    phone: str 
