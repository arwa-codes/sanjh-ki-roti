from typing import List
from sqlalchemy.orm import Session
from app.models.notification import NotificationQueue
from app.repositories.base import BaseRepository

class NotificationQueueRepository(BaseRepository[NotificationQueue]):
    def get_pending_notifications(self, db: Session) -> List[NotificationQueue]:
        """Fetch all notifications that are pending dispatch (status = 'pending')."""
        return db.query(self.model).filter(self.model.status == "pending").all()

# Global repository instance
notification_queue_repository = NotificationQueueRepository(NotificationQueue)
