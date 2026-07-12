from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.plan import Plan
from app.repositories.base import BaseRepository

class PlanRepository(BaseRepository[Plan]):
    def get_by_name(self, db: Session, name: str) -> Optional[Plan]:
        """Fetch a plan by its unique name."""
        return db.query(self.model).filter(self.model.name == name).first()

    def get_active_plans(self, db: Session) -> List[Plan]:
        """Fetch all currently active plans."""
        return db.query(self.model).filter(self.model.is_active == True).all()

# Global repository instance
plan_repository = PlanRepository(Plan)
