from datetime import datetime, timedelta
from typing import Any, List
from sqlalchemy.orm import Session
from app.models.complaint import Complaint
from app.repositories.base import BaseRepository

class ComplaintRepository(BaseRepository[Complaint]):
    def get_by_customer_id(self, db: Session, customer_id: Any) -> List[Complaint]:
        """Fetch all complaints logged by a customer."""
        return db.query(self.model).filter(self.model.customer_id == customer_id).all()

    def get_open_older_than(self, db: Session, hours: int) -> List[Complaint]:
        """Fetch all open complaints older than the specified hours (used for SLA escalation scans)."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return db.query(self.model).filter(
            self.model.status == "open",
            self.model.created_at < cutoff_time
        ).all()

# Global repository instance
complaint_repository = ComplaintRepository(Complaint)
