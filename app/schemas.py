from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "employee"
    department: Optional[str] = None
    support_team_id: Optional[int] = None

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    department: Optional[str] = None
    support_team_id: Optional[int] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class TicketCreate(BaseModel):
    subject: str
    description: str
    category: str
    priority: str
    asset_id: Optional[int] = None
    support_team_id: Optional[int] = None

class TicketUpdate(BaseModel):
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None

class AssignTicket(BaseModel):
    assigned_agent_id: Optional[int] = None

class StatusUpdate(BaseModel):
    status: str

class ResolveTicket(BaseModel):
    resolution_details: str

class CommentCreate(BaseModel):
    content: str
    is_internal: bool = False

class AssetCreate(BaseModel):
    asset_name: str
    asset_type: str
    serial_number: str
    assigned_employee_id: Optional[int] = None
    department: Optional[str] = None
    purchase_date: Optional[datetime] = None

class AssetUpdate(BaseModel):
    asset_name: Optional[str] = None
    asset_type: Optional[str] = None
    assigned_employee_id: Optional[int] = None
    department: Optional[str] = None
    status: Optional[str] = None

class SLARuleUpdate(BaseModel):
    response_hours: float
    resolution_hours: float
