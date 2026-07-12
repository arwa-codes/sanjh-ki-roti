from typing import Any, List, Optional
from sqlalchemy.orm import Session
from app.models.billing import BillingTransaction, MealAddon, Referral
from app.repositories.base import BaseRepository

class BillingTransactionRepository(BaseRepository[BillingTransaction]):
    def get_by_customer_id(self, db: Session, customer_id: Any) -> List[BillingTransaction]:
        """Fetch all invoices and transactions for a customer."""
        return db.query(self.model).filter(self.model.customer_id == customer_id).all()

    def get_by_gateway_id(self, db: Session, gateway_transaction_id: str) -> Optional[BillingTransaction]:
        """Fetch a transaction by gateway ID (useful for webhooks)."""
        return db.query(self.model).filter(self.model.gateway_transaction_id == gateway_transaction_id).first()

class MealAddonRepository(BaseRepository[MealAddon]):
    def get_by_subscription_id(self, db: Session, subscription_id: Any) -> List[MealAddon]:
        """Fetch all add-on items associated with a subscription."""
        return db.query(self.model).filter(self.model.subscription_id == subscription_id).all()

class ReferralRepository(BaseRepository[Referral]):
    def get_by_referee_id(self, db: Session, referee_id: Any) -> Optional[Referral]:
        """Fetch referral tracking mapping by the referee's ID."""
        return db.query(self.model).filter(self.model.referee_id == referee_id).first()

    def get_by_referrer_id(self, db: Session, referrer_id: Any) -> List[Referral]:
        """Fetch all referrals made by a referrer customer."""
        return db.query(self.model).filter(self.model.referrer_id == referrer_id).all()

# Global repository instances
billing_transaction_repository = BillingTransactionRepository(BillingTransaction)
meal_addon_repository = MealAddonRepository(MealAddon)
referral_repository = ReferralRepository(Referral)
