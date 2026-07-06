from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserBase(BaseModel):
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15, pattern=r"^\+?[0-9\-\s]+$")
    role: str = Field("customer", pattern=r"^(admin|delivery|customer)$")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=15, pattern=r"^\+?[0-9\-\s]+$")
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None
