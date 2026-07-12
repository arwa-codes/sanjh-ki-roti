import json
from datetime import date
from typing import Any, List, Optional
from sqlalchemy.orm import Session
from app.models.delivery import Route, DeliveryPartner, DeliveryLog
from app.repositories.base import BaseRepository

class RouteRepository(BaseRepository[Route]):
    def get_by_name(self, db: Session, name: str) -> Optional[Route]:
        """Fetch a route by its unique name."""
        return db.query(self.model).filter(self.model.name == name).first()

    def get_by_pincode(self, db: Session, pincode: str) -> Optional[Route]:
        """Find an active route mapping a specific postal code (SQL text matching for cross-db compatibility)."""
        return db.query(self.model).filter(
            self.model.is_active == True,
            self.model.pincodes.like(f'%"{pincode}"%')
        ).first()

class DeliveryPartnerRepository(BaseRepository[DeliveryPartner]):
    def get_by_user_id(self, db: Session, user_id: Any) -> Optional[DeliveryPartner]:
        """Fetch a delivery partner profile details by user ID link."""
        return db.query(self.model).filter(self.model.user_id == user_id).first()

    def get_by_dl_number(self, db: Session, dl_number: str) -> Optional[DeliveryPartner]:
        """Fetch a delivery partner by their unique DL number."""
        return db.query(self.model).filter(self.model.dl_number == dl_number).first()

    def get_active_partners_on_route(self, db: Session, route_id: Any) -> List[DeliveryPartner]:
        """Fetch verified active delivery partners assigned to a specific route."""
        return db.query(self.model).filter(
            self.model.current_route_id == route_id,
            self.model.is_active == True,
            self.model.is_verified == True
        ).all()

class DeliveryLogRepository(BaseRepository[DeliveryLog]):
    def get_route_sheet_for_partner(self, db: Session, partner_id: Any, delivery_date: date) -> List[DeliveryLog]:
        """Get the daily run sheet for a delivery driver on a specific date."""
        return db.query(self.model).filter(
            self.model.delivery_partner_id == partner_id,
            self.model.delivery_date == delivery_date
        ).all()

    def get_logs_for_date_and_meal(self, db: Session, delivery_date: date, meal_type: str) -> List[DeliveryLog]:
        """Get all scheduled runs on a given date for a specific meal type (lunch/dinner)."""
        return db.query(self.model).filter(
            self.model.delivery_date == delivery_date,
            self.model.meal_type == meal_type
        ).all()

    def get_active_logs_by_subscription(self, db: Session, subscription_id: Any) -> List[DeliveryLog]:
        """Retrieve all deliveries logged under a subscription."""
        return db.query(self.model).filter(self.model.subscription_id == subscription_id).all()

# Global repository instances
route_repository = RouteRepository(Route)
delivery_partner_repository = DeliveryPartnerRepository(DeliveryPartner)
delivery_log_repository = DeliveryLogRepository(DeliveryLog)
