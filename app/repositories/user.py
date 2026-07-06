from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Fetch a user by their unique email address."""
        return db.query(self.model).filter(self.model.email == email).first()

    def get_by_phone(self, db: Session, phone: str) -> Optional[User]:
        """Fetch a user by their unique phone number."""
        return db.query(self.model).filter(self.model.phone == phone).first()

# Global repository instance
user_repository = UserRepository(User)
