import json
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator

class RouteBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    area: str = Field(..., min_length=2, max_length=100)
    pincodes: List[str] = Field(..., min_length=1)

class RouteCreate(RouteBase):
    pass

class RouteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    area: Optional[str] = Field(None, min_length=2, max_length=100)
    pincodes: Optional[List[str]] = None
    is_active: Optional[bool] = None

class RouteResponse(RouteBase):
    id: UUID
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

    @field_validator("pincodes", mode="before")
    @classmethod
    def parse_pincodes(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

class DeliveryPartnerBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    dl_number: str = Field(..., min_length=5, max_length=20)

class DeliveryPartnerCreate(DeliveryPartnerBase):
    pass

class DeliveryPartnerUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    dl_number: Optional[str] = Field(None, min_length=5, max_length=20)
    current_route_id: Optional[UUID] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None

class DeliveryPartnerResponse(DeliveryPartnerBase):
    id: UUID
    user_id: UUID
    document_url: Optional[str] = None
    is_verified: bool
    current_route_id: Optional[UUID] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class DeliveryLogResponse(BaseModel):
    id: UUID
    subscription_id: UUID
    delivery_partner_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    delivery_date: date
    meal_type: str
    status: str
    failure_reason: Optional[str] = None
    delivered_at: Optional[datetime] = None
    photo_proof_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DeliveryLogStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(out_for_delivery|delivered|failed)$")
    failure_reason: Optional[str] = Field(None, max_length=255)
    photo_proof_url: Optional[str] = None
