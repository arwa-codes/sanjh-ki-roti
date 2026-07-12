import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.delivery import Route, DeliveryPartner, DeliveryLog
from app.models.subscription import Subscription, SubscriptionPause
from app.models.customer import Customer
from app.schemas.delivery import RouteCreate, RouteUpdate, DeliveryPartnerCreate, DeliveryPartnerUpdate, DeliveryLogStatusUpdate
from app.repositories.delivery import route_repository, delivery_partner_repository, delivery_log_repository
from app.repositories.subscription import subscription_repository
from app.repositories.customer import customer_repository
from app.core.exceptions import EntityNotFoundException, EntityAlreadyExistsException, ForbiddenException
from app.services.subscription_service import get_ist_now

class DeliveryService:
    def create_route(self, db: Session, route_in: RouteCreate) -> Route:
        """Create a new delivery route representing areas and pincodes."""
        if route_repository.get_by_name(db, name=route_in.name):
            raise EntityAlreadyExistsException("A route with this name already exists.")

        route_data = {
            "name": route_in.name,
            "area": route_in.area,
            "pincodes": json.dumps(route_in.pincodes),
            "is_active": True
        }
        return route_repository.create(db, obj_in=route_data)

    def create_delivery_partner(
        self, db: Session, user_id: UUID, partner_in: DeliveryPartnerCreate
    ) -> DeliveryPartner:
        """Register a delivery partner profile."""
        if delivery_partner_repository.get_by_user_id(db, user_id=user_id):
            raise EntityAlreadyExistsException("Delivery partner profile already exists for this user.")

        if delivery_partner_repository.get_by_dl_number(db, dl_number=partner_in.dl_number):
            raise EntityAlreadyExistsException("A partner with this DL number already exists.")

        partner_data = {
            "user_id": user_id,
            "first_name": partner_in.first_name,
            "last_name": partner_in.last_name,
            "dl_number": partner_in.dl_number,
            "is_verified": False,
            "is_active": True
        }
        return delivery_partner_repository.create(db, obj_in=partner_data)

    def upload_dl_document(
        self, db: Session, partner_id: UUID, file_content: bytes, filename: str
    ) -> str:
        """Simulate secure document upload for Driving Licenses."""
        partner = delivery_partner_repository.get(db, id=partner_id)
        if not partner:
            raise EntityNotFoundException("Delivery partner profile not found.")

        ext = filename.split(".")[-1].lower()
        if ext not in ["pdf", "jpg", "jpeg", "png"]:
            raise ValueError("Invalid document type. Allowed types are PDF, JPG, JPEG, PNG.")

        if len(file_content) > 5 * 1024 * 1024:
            raise ValueError("File exceeds maximum allowed size of 5MB.")

        mock_url = f"https://mock-s3-bucket.s3.amazonaws.com/uploads/dl/{partner_id}.{ext}"
        delivery_partner_repository.update(db, db_obj=partner, obj_in={"document_url": mock_url})
        return mock_url

    def verify_partner(self, db: Session, partner_id: UUID, is_verified: bool) -> DeliveryPartner:
        """Verify delivery partner's DL and documents (Admin action)."""
        partner = delivery_partner_repository.get(db, id=partner_id)
        if not partner:
            raise EntityNotFoundException("Delivery partner profile not found.")

        return delivery_partner_repository.update(db, db_obj=partner, obj_in={"is_verified": is_verified})

    def assign_route(self, db: Session, partner_id: UUID, route_id: UUID) -> DeliveryPartner:
        """Assign an active route to a delivery partner."""
        partner = delivery_partner_repository.get(db, id=partner_id)
        if not partner:
            raise EntityNotFoundException("Delivery partner not found.")

        route = route_repository.get(db, id=route_id)
        if not route or not route.is_active:
            raise EntityNotFoundException("Active route not found.")

        return delivery_partner_repository.update(db, db_obj=partner, obj_in={"current_route_id": route_id})

    def generate_daily_delivery_logs(self, db: Session, delivery_date: date, meal_type: str) -> List[DeliveryLog]:
        """Auto-generate daily meal delivery runs for active, non-paused subscriptions."""
        generated_logs = []
        
        # Get all subscriptions
        subscriptions = db.query(Subscription).filter(Subscription.status == "active").all()

        for sub in subscriptions:
            # 1. Date range bounds checks
            if not (sub.start_date <= delivery_date <= sub.end_date):
                continue

            # 2. Check remaining meals tally
            if sub.remaining_meals <= 0:
                # Suspend expired active plans
                subscription_repository.update(db, db_obj=sub, obj_in={"status": "expired"})
                continue

            # 3. Check meal inclusions eligibility
            plan = sub.plan
            if meal_type == "lunch" and plan.meals_included not in ["lunch", "both"]:
                continue
            if meal_type == "dinner" and plan.meals_included not in ["dinner", "both"]:
                continue

            # 4. Check active pauses covering this date
            is_paused = False
            for pause in sub.pauses:
                if pause.status in ["active", "pending", "completed"]:
                    if pause.start_date <= delivery_date <= pause.end_date:
                        is_paused = True
                        break
            if is_paused:
                continue

            # 5. Check if delivery log was already generated for this meal slot
            existing_log = db.query(DeliveryLog).filter(
                DeliveryLog.subscription_id == sub.id,
                DeliveryLog.delivery_date == delivery_date,
                DeliveryLog.meal_type == meal_type
            ).first()
            if existing_log:
                continue

            # 6. Locate customer route assignment by pincode
            customer = sub.customer
            route = route_repository.get_by_pincode(db, pincode=customer.pincode)
            if not route:
                continue

            # Update customer route details if not already assigned
            if customer.route_id != route.id:
                customer_repository.update(db, db_obj=customer, obj_in={"route_id": route.id})

            # Get active verified partner assigned to this route
            partners = delivery_partner_repository.get_active_partners_on_route(db, route_id=route.id)
            partner = partners[0] if partners else None

            # Create delivery log
            log_data = {
                "subscription_id": sub.id,
                "delivery_partner_id": partner.id if partner else None,
                "route_id": route.id,
                "delivery_date": delivery_date,
                "meal_type": meal_type,
                "status": "pending"
            }
            log = delivery_log_repository.create(db, obj_in=log_data)
            generated_logs.append(log)

            # Deduct meal from remaining count
            new_remaining = sub.remaining_meals - 1
            update_fields = {"remaining_meals": new_remaining}
            if new_remaining <= 0:
                update_fields["status"] = "expired"
            subscription_repository.update(db, db_obj=sub, obj_in=update_fields)

        return generated_logs

    def update_delivery_status(
        self, db: Session, log_id: UUID, status_in: DeliveryLogStatusUpdate
    ) -> DeliveryLog:
        """Update meal delivery progress and status flags."""
        log = delivery_log_repository.get(db, id=log_id)
        if not log:
            raise EntityNotFoundException("Delivery log not found.")

        update_data = {
            "status": status_in.status,
            "failure_reason": status_in.failure_reason,
            "photo_proof_url": status_in.photo_proof_url
        }

        if status_in.status == "delivered":
            update_data["delivered_at"] = get_ist_now()

        if status_in.status == "failed" and not status_in.failure_reason:
            raise ForbiddenException("A failure reason must be provided when marking delivery as failed.")

        return delivery_log_repository.update(db, db_obj=log, obj_in=update_data)

    def get_admin_dashboard_stats(self, db: Session) -> dict:
        """Fetch kitchen meal prep counters and operational driver statistics."""
        ist_today = get_ist_now().date()

        active_subs = db.query(Subscription).filter(Subscription.status == "active").count()
        
        lunch_count = db.query(DeliveryLog).filter(
            DeliveryLog.delivery_date == ist_today,
            DeliveryLog.meal_type == "lunch"
        ).count()

        dinner_count = db.query(DeliveryLog).filter(
            DeliveryLog.delivery_date == ist_today,
            DeliveryLog.meal_type == "dinner"
        ).count()

        active_drivers = db.query(DeliveryPartner).filter(
            DeliveryPartner.is_active == True,
            DeliveryPartner.is_verified == True
        ).count()

        # Count active routes that do not have an active and verified partner assigned
        unassigned_routes = 0
        all_active_routes = db.query(Route).filter(Route.is_active == True).all()
        for r in all_active_routes:
            partners = delivery_partner_repository.get_active_partners_on_route(db, route_id=r.id)
            if not partners:
                unassigned_routes += 1

        return {
            "active_subscriptions": active_subs,
            "lunch_meal_prep_count": lunch_count,
            "dinner_meal_prep_count": dinner_count,
            "active_drivers_count": active_drivers,
            "unassigned_routes_count": unassigned_routes
        }

# Global delivery service instance
delivery_service = DeliveryService()
