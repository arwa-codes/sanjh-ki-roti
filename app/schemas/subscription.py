from datetime import date, datetime
from typing import Optional
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class SubscriptionCreate(BaseModel):
    plan_id: UUID

class SubscriptionResponse(BaseModel):
    id: UUID
    customer_id: UUID
    plan_id: UUID
    status: str
    start_date: date
    end_date: date
    remaining_meals: int
    original_price: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SubscriptionPauseCreate(BaseModel):
    start_date: date
    end_date: date

class SubscriptionPauseResponse(BaseModel):
    id: UUID
    subscription_id: UUID
    start_date: date
    end_date: date
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
