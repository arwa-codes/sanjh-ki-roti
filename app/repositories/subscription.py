from typing import Any, List, Optional
from sqlalchemy.orm import Session
from app.models.subscription import Subscription, SubscriptionPause
from app.repositories.base import BaseRepository

class SubscriptionRepository(BaseRepository[Subscription]):
    def get_by_customer_id(self, db: Session, customer_id: Any) -> List[Subscription]:
        """Fetch all subscriptions purchased by a customer."""
        return db.query(self.model).filter(self.model.customer_id == customer_id).all()

    def get_active_subscription(self, db: Session, customer_id: Any) -> Optional[Subscription]:
        """Get the current active or paused subscription for a customer."""
        return db.query(self.model).filter(
            self.model.customer_id == customer_id,
            self.model.status.in_(["active", "paused"])
        ).first()

class SubscriptionPauseRepository(BaseRepository[SubscriptionPause]):
    def get_by_subscription_id(self, db: Session, subscription_id: Any) -> List[SubscriptionPause]:
        """Fetch all pause periods mapped to a subscription."""
        return db.query(self.model).filter(self.model.subscription_id == subscription_id).all()

    def get_active_pause(self, db: Session, subscription_id: Any) -> Optional[SubscriptionPause]:
        """Get the currently active pause period for a subscription."""
        return db.query(self.model).filter(
            self.model.subscription_id == subscription_id,
            self.model.status == "active"
        ).first()

# Global repository instances
subscription_repository = SubscriptionRepository(Subscription)
subscription_pause_repository = SubscriptionPauseRepository(SubscriptionPause)
