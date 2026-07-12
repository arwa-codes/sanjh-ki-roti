from typing import Optional
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class PlanBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    duration_days: int = Field(..., gt=0, description="Duration in days")
    price: Decimal = Field(..., gt=0, decimal_places=2)
    meals_included: str = Field("both", pattern=r"^(lunch|dinner|both)$")

class PlanCreate(PlanBase):
    pass

class PlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    duration_days: Optional[int] = Field(None, gt=0)
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    meals_included: Optional[str] = Field(None, pattern=r"^(lunch|dinner|both)$")
    is_active: Optional[bool] = None

class PlanResponse(PlanBase):
    id: UUID
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
