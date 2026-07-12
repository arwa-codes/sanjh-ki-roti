from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.billing import BillingTransactionResponse, WebhookPayload
from app.services.billing_service import billing_service
from app.repositories.billing import billing_transaction_repository
from app.repositories.customer import customer_repository
from app.api.dependencies import get_current_user
from app.models.user import User
from app.core.exceptions import ForbiddenException

router = APIRouter()

@router.get(
    "/invoices",
    response_model=List[BillingTransactionResponse],
    summary="List customer invoices"
)
def list_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[BillingTransactionResponse]:
    """Retrieve all invoice records and transactions. Customers view own; Admins view all."""
    if current_user.role == "admin":
        return billing_transaction_repository.get_multi(db)
        
    profile = customer_repository.get_by_user_id(db, user_id=current_user.id)
    if not profile:
        raise ForbiddenException("Customer profile not found.")
        
    return billing_transaction_repository.get_by_customer_id(db, customer_id=profile.id)

@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Receive payment gateway status webhooks"
)
def handle_payment_webhook(
    payload: WebhookPayload,
    db: Session = Depends(get_db)
) -> dict:
    """Process incoming payment status notifications from Stripe/Razorpay."""
    billing_service.process_payment_webhook(db, payload=payload)
    return {"status": "success", "message": "Webhook processed and transaction updated."}
