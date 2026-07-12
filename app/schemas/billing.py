from datetime import date
from typing import Optional
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class BillingTransactionResponse(BaseModel):
    id: UUID
    customer_id: UUID
    subscription_id: Optional[UUID] = None
    billing_date: date
    amount: Decimal
    payment_status: str
    gateway_transaction_id: Optional[str] = None
    invoice_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class MealAddonCreate(BaseModel):
    addon_date: date
    meal_type: str = Field(..., pattern=r"^(lunch|dinner)$")
    addon_type: str = Field(..., pattern=r"^(extra_roti|sweet|buttermilk)$")
    quantity: int = Field(1, gt=0)

class MealAddonResponse(BaseModel):
    id: UUID
    subscription_id: UUID
    addon_date: date
    meal_type: str
    addon_type: str
    quantity: int
    price: Decimal
    is_paid: bool

    model_config = ConfigDict(from_attributes=True)

class WebhookPayload(BaseModel):
    event: str  # e.g., payment.captured, payment.failed
    transaction_id: str
    payment_status: str  # paid | failed
    amount: Decimal
