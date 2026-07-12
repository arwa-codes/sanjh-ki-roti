import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.notification import NotificationQueue
from app.repositories.notification import notification_queue_repository

logger = logging.getLogger(__name__)

class NotificationService:
    def queue_notification(self, db: Session, recipient: str, subject: str, body: str) -> NotificationQueue:
        """Add a notification to the outbox queue."""
        notification_data = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "status": "pending"
        }
        return notification_queue_repository.create(db, obj_in=notification_data)

    def process_outbox_notifications(self, db: Session) -> int:
        """Poll the outbox queue and mock dispatch SMTP emails."""
        processed_count = 0
        pending_list = notification_queue_repository.get_pending_notifications(db)

        for notification in pending_list:
            try:
                # Simulated SMTP delivery logging
                logger.info(
                    f"--- MOCK SMTP EMAIL DISPATCH ---\n"
                    f"To: {notification.recipient}\n"
                    f"Subject: {notification.subject}\n"
                    f"Body: {notification.body}\n"
                    f"--------------------------------"
                )
                
                # Update status to sent
                notification_queue_repository.update(
                    db,
                    db_obj=notification,
                    obj_in={
                        "status": "sent",
                        "sent_at": datetime.utcnow()
                    }
                )
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to dispatch email {notification.id}: {str(e)}")
                notification_queue_repository.update(
                    db,
                    db_obj=notification,
                    obj_in={
                        "status": "failed",
                        "error_message": str(e)
                    }
                )

        return processed_count

# Global notification service instance
notification_service = NotificationService()
