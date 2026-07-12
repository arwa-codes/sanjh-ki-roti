from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.subscription import Subscription, SubscriptionPause
from app.models.billing import MealAddon, BillingTransaction
from app.schemas.subscription import SubscriptionPauseCreate
from app.schemas.billing import MealAddonCreate
from app.repositories.customer import customer_repository
from app.repositories.plan import plan_repository
from app.repositories.subscription import subscription_repository, subscription_pause_repository
from app.repositories.billing import meal_addon_repository, billing_transaction_repository
from app.core.exceptions import EntityNotFoundException, EntityAlreadyExistsException, ForbiddenException

# India Standard Time offset helper
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now() -> datetime:
    """Return current datetime in India Standard Time (UTC+05:30)."""
    return datetime.now(timezone.utc).astimezone(IST)

class SubscriptionService:
    def purchase_subscription(self, db: Session, customer_id: UUID, plan_id: UUID) -> Subscription:
        """Initiate plan purchase and generate an unpaid transaction invoice."""
        customer = customer_repository.get(db, id=customer_id)
        if not customer:
            raise EntityNotFoundException("Customer profile not found.")
            
        if not customer.is_verified:
            raise ForbiddenException("Customer profile must be verified before purchasing.")

        plan = plan_repository.get(db, id=plan_id)
        if not plan:
            raise EntityNotFoundException("Subscription plan not found.")
            
        if not plan.is_active:
            raise ForbiddenException("This subscription plan is currently inactive.")

        # Check for pre-existing active/paused subscriptions
        active_sub = subscription_repository.get_active_subscription(db, customer_id=customer_id)
        if active_sub:
            raise EntityAlreadyExistsException("Customer already has an active subscription plan.")

        # Calculate subscription details
        ist_now = get_ist_now()
        start_date = ist_now.date()
        end_date = start_date + timedelta(days=plan.duration_days)
        
        factor = 2 if plan.meals_included == "both" else 1
        remaining_meals = plan.duration_days * factor

        # Create Subscription record with pending status
        sub_data = {
            "customer_id": customer_id,
            "plan_id": plan_id,
            "status": "pending",  # pending until payment transaction webhook executes
            "start_date": start_date,
            "end_date": end_date,
            "remaining_meals": remaining_meals,
            "original_price": plan.price
        }
        subscription = subscription_repository.create(db, obj_in=sub_data)

        # Generate accompanying unpaid billing transaction invoice
        tx_data = {
            "customer_id": customer_id,
            "subscription_id": subscription.id,
            "billing_date": start_date,
            "amount": plan.price,
            "payment_status": "unpaid",
            "gateway_transaction_id": f"TXN-SUB-{str(subscription.id)[:8].upper()}",
            "invoice_url": f"https://mock-invoice-service.sanjh.com/invoices/{subscription.id}.pdf"
        }
        billing_transaction_repository.create(db, obj_in=tx_data)

        return subscription

    def pause_subscription(
        self, db: Session, subscription_id: UUID, pause_in: SubscriptionPauseCreate
    ) -> SubscriptionPause:
        """Schedule a pause interval, validating cutoff times for same-day requests."""
        subscription = subscription_repository.get(db, id=subscription_id)
        if not subscription:
            raise EntityNotFoundException("Subscription not found.")
            
        if subscription.status not in ["active", "paused"]:
            raise ForbiddenException("Only active or paused subscriptions can be paused.")

        # Validate pause date parameters
        ist_now = get_ist_now()
        today = ist_now.date()

        if pause_in.start_date < today:
            raise ForbiddenException("Pause start date cannot occur in the past.")
            
        if pause_in.end_date < pause_in.start_date:
            raise ForbiddenException("Pause end date cannot occur before start date.")

        # Enforce same-day cutoff times: 08:00 AM (Lunch) or 04:00 PM (Dinner)
        if pause_in.start_date == today:
            plan = subscription.plan
            current_hour = ist_now.hour
            current_minute = ist_now.minute

            if plan.meals_included in ["lunch", "both"]:
                # Cutoff for lunch same-day is 08:00 AM
                if current_hour > 8 or (current_hour == 8 and current_minute > 0):
                    raise ForbiddenException("Cutoff expired. Lunch pause request must be before 08:00 AM.")
            elif plan.meals_included == "dinner":
                # Cutoff for dinner same-day is 04:00 PM (16:00)
                if current_hour > 16 or (current_hour == 16 and current_minute > 0):
                    raise ForbiddenException("Cutoff expired. Dinner pause request must be before 04:00 PM.")

        # Check for overlaps
        all_pauses = subscription_pause_repository.get_by_subscription_id(db, subscription_id=subscription_id)
        for p in all_pauses:
            if p.status != "completed" and not (pause_in.end_date < p.start_date or pause_in.start_date > p.end_date):
                raise EntityAlreadyExistsException("This pause interval overlaps with an existing scheduled pause.")

        # Create Pause record
        status = "active" if pause_in.start_date == today else "pending"
        pause_data = {
            "subscription_id": subscription_id,
            "start_date": pause_in.start_date,
            "end_date": pause_in.end_date,
            "status": status
        }
        pause = subscription_pause_repository.create(db, obj_in=pause_data)

        # Update parent subscription status immediately if pause is effective today
        if status == "active":
            subscription_repository.update(db, db_obj=subscription, obj_in={"status": "paused"})

        return pause

    def resume_subscription(self, db: Session, subscription_id: UUID) -> Subscription:
        """Cancel an active pause period and recalculate validity extensions."""
        subscription = subscription_repository.get(db, id=subscription_id)
        if not subscription:
            raise EntityNotFoundException("Subscription not found.")

        active_pause = subscription_pause_repository.get_active_pause(db, subscription_id=subscription_id)
        if not active_pause:
            raise EntityNotFoundException("No active pause found for this subscription.")

        ist_now = get_ist_now()
        today = ist_now.date()

        # Calculate actual paused days to extend subscription end_date
        # If early resume occurs today, actual days = today - start_date
        actual_paused_days = (today - active_pause.start_date).days
        if actual_paused_days < 0:
            actual_paused_days = 0

        # Adjust subscription end date
        original_extension_days = (active_pause.end_date - active_pause.start_date).days + 1
        new_extension_days = actual_paused_days
        reduction = original_extension_days - new_extension_days

        # Extend subscription end_date by the number of actual days paused
        new_end_date = subscription.end_date - timedelta(days=reduction)
        if actual_paused_days > 0:
            new_end_date = subscription.end_date + timedelta(days=actual_paused_days)

        # Complete the pause
        subscription_pause_repository.update(
            db,
            db_obj=active_pause,
            obj_in={"status": "completed", "resolved_at": ist_now, "end_date": today}
        )

        # Restore subscription status to active
        return subscription_repository.update(
            db,
            db_obj=subscription,
            obj_in={"status": "active", "end_date": new_end_date}
        )

    def request_addon(self, db: Session, subscription_id: UUID, addon_in: MealAddonCreate) -> MealAddon:
        """Create a daily meal add-on, validating cutoff times."""
        subscription = subscription_repository.get(db, id=subscription_id)
        if not subscription:
            raise EntityNotFoundException("Subscription not found.")

        if subscription.status != "active":
            raise ForbiddenException("Add-ons can only be added to active subscriptions.")

        ist_now = get_ist_now()
        today = ist_now.date()

        if addon_in.addon_date < today:
            raise ForbiddenException("Add-on date cannot occur in the past.")

        # Verify same-day cutoff times
        if addon_in.addon_date == today:
            current_hour = ist_now.hour
            current_minute = ist_now.minute

            if addon_in.meal_type == "lunch":
                if current_hour > 8 or (current_hour == 8 and current_minute > 0):
                    raise ForbiddenException("Cutoff expired. Lunch add-on request must be before 08:00 AM.")
            elif addon_in.meal_type == "dinner":
                if current_hour > 16 or (current_hour == 16 and current_minute > 0):
                    raise ForbiddenException("Cutoff expired. Dinner add-on request must be before 04:00 PM.")

        # Addon pricing mapping
        pricing = {"extra_roti": 10.00, "sweet": 30.00, "buttermilk": 20.00}
        unit_price = pricing.get(addon_in.addon_type, 15.00)
        total_price = unit_price * addon_in.quantity

        # Create MealAddon
        addon_data = {
            "subscription_id": subscription_id,
            "addon_date": addon_in.addon_date,
            "meal_type": addon_in.meal_type,
            "addon_type": addon_in.addon_type,
            "quantity": addon_in.quantity,
            "price": total_price,
            "is_paid": False
        }
        addon = meal_addon_repository.create(db, obj_in=addon_data)

        # Generate unpaid billing transaction invoice for the add-on
        tx_data = {
            "customer_id": subscription.customer_id,
            "subscription_id": subscription_id,
            "billing_date": today,
            "amount": total_price,
            "payment_status": "unpaid",
            "gateway_transaction_id": f"TXN-ADDON-{str(addon.id)[:8].upper()}"
        }
        billing_transaction_repository.create(db, obj_in=tx_data)

        return addon

# Global subscription service instance
subscription_service = SubscriptionService()
