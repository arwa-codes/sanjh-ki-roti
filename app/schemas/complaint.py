from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class ComplaintBase(BaseModel):
    category: str = Field(..., pattern=r"^(quality|quantity|delay|behavior)$")
    description: str = Field(..., min_length=5, max_length=500)

class ComplaintCreate(ComplaintBase):
    delivery_log_id: UUID

class ComplaintResolve(BaseModel):
    status: str = Field("resolved", pattern=r"^(resolved)$")
    resolution_notes: str = Field(..., min_length=5, max_length=500)

class ComplaintResponse(ComplaintBase):
    id: UUID
    customer_id: UUID
    delivery_log_id: UUID
    status: str
    resolution_notes: Optional[str] = None
    assigned_admin_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
