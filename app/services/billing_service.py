from sqlalchemy.orm import Session
from app.schemas.billing import WebhookPayload
from app.models.billing import BillingTransaction
from app.repositories.billing import billing_transaction_repository, referral_repository, meal_addon_repository
from app.repositories.subscription import subscription_repository
from app.core.exceptions import EntityNotFoundException, ForbiddenException

class BillingService:
    def process_payment_webhook(self, db: Session, payload: WebhookPayload) -> BillingTransaction:
        """Process mock payment gateway webhook and update transaction/subscription states."""
        transaction = billing_transaction_repository.get_by_gateway_id(
            db, gateway_transaction_id=payload.transaction_id
        )
        if not transaction:
            raise EntityNotFoundException("Billing transaction record not found.")

        # Update payment transaction status
        billing_transaction_repository.update(
            db, db_obj=transaction, obj_in={"payment_status": payload.payment_status}
        )

        if payload.payment_status == "paid":
            # If the transaction is associated with a subscription plan activation
            if transaction.subscription_id:
                subscription = subscription_repository.get(db, id=transaction.subscription_id)
                if subscription:
                    # Update subscription status to active
                    subscription_repository.update(db, db_obj=subscription, obj_in={"status": "active"})

                    # Process Referral system credit unlock logic
                    # Check if this customer was referred by another verified user
                    ref_record = referral_repository.get_by_referee_id(db, referee_id=transaction.customer_id)
                    if ref_record and ref_record.status == "pending":
                        plan = subscription.plan
                        # Unlock referral if referee purchases their first monthly plan
                        if plan.duration_days >= 30:
                            # Set status to claimed once their monthly plan goes active
                            referral_repository.update(db, db_obj=ref_record, obj_in={"status": "claimed"})

            # If the transaction is associated with a daily meal addon payment
            if payload.transaction_id.startswith("TXN-ADDON-"):
                addon_prefix = payload.transaction_id.replace("TXN-ADDON-", "").lower()
                if transaction.subscription_id:
                    all_addons = meal_addon_repository.get_by_subscription_id(
                        db, subscription_id=transaction.subscription_id
                    )
                    # Match addon by ID prefix
                    for addon in all_addons:
                        if str(addon.id).startswith(addon_prefix):
                            meal_addon_repository.update(db, db_obj=addon, obj_in={"is_paid": True})
                            break

        return transaction

# Global billing service instance
billing_service = BillingService()
