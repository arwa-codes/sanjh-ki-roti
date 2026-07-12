from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class CustomerBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    address: str = Field(..., min_length=5, max_length=255)
    pincode: str = Field(..., min_length=6, max_length=6, pattern=r"^[0-9]{6}$")
    aadhaar_number: str = Field(..., min_length=12, max_length=12, pattern=r"^[0-9]{12}$")

class CustomerCreate(CustomerBase):
    referral_code: Optional[str] = Field(None, description="Optional referral code of another customer")

class CustomerUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    address: Optional[str] = Field(None, min_length=5, max_length=255)
    pincode: Optional[str] = Field(None, min_length=6, max_length=6, pattern=r"^[0-9]{6}$")
    document_url: Optional[str] = None
    is_verified: Optional[bool] = None

class CustomerResponse(CustomerBase):
    id: UUID
    user_id: UUID
    route_id: Optional[UUID] = None
    document_url: Optional[str] = None
    is_verified: bool
    referral_code: str
    referred_by_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)
