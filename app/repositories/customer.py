from typing import Any, Optional
from sqlalchemy.orm import Session
from app.models.customer import Customer
from app.repositories.base import BaseRepository

class CustomerRepository(BaseRepository[Customer]):
    def get_by_user_id(self, db: Session, user_id: Any) -> Optional[Customer]:
        """Fetch customer profile details by mapped User ID."""
        return db.query(self.model).filter(self.model.user_id == user_id).first()

    def get_by_referral_code(self, db: Session, referral_code: str) -> Optional[Customer]:
        """Fetch customer profile details by referral code."""
        return db.query(self.model).filter(self.model.referral_code == referral_code).first()

    def get_by_aadhaar(self, db: Session, aadhaar_number: str) -> Optional[Customer]:
        """Fetch customer profile details by Aadhaar number."""
        return db.query(self.model).filter(self.model.aadhaar_number == aadhaar_number).first()

# Global repository instance
customer_repository = CustomerRepository(Customer)
