from uuid import UUID
from sqlalchemy.orm import Session
from app.models.complaint import Complaint
from app.schemas.complaint import ComplaintCreate, ComplaintResolve
from app.repositories.complaint import complaint_repository
from app.repositories.customer import customer_repository
from app.repositories.delivery import delivery_log_repository
from app.services.notification_service import notification_service
from app.core.exceptions import EntityNotFoundException, ForbiddenException

class ComplaintService:
    def create_complaint(self, db: Session, customer_id: UUID, complaint_in: ComplaintCreate) -> Complaint:
        """Log a new complaint against a delivery log run and notify customer."""
        customer = customer_repository.get(db, id=customer_id)
        if not customer:
            raise EntityNotFoundException("Customer profile not found.")

        delivery_log = delivery_log_repository.get(db, id=complaint_in.delivery_log_id)
        if not delivery_log:
            raise EntityNotFoundException("Delivery log run not found.")

        # Ensure the log belongs to the filing customer
        if delivery_log.subscription.customer_id != customer_id:
            raise ForbiddenException("Cannot file a complaint against a run that does not belong to your subscription.")

        # Check if a complaint has already been logged for this delivery run
        existing = db.query(Complaint).filter(Complaint.delivery_log_id == complaint_in.delivery_log_id).first()
        if existing:
            raise ForbiddenException("A complaint has already been logged for this delivery run.")

        complaint_data = {
            "customer_id": customer_id,
            "delivery_log_id": complaint_in.delivery_log_id,
            "category": complaint_in.category,
            "description": complaint_in.description,
            "status": "open"
        }
        complaint = complaint_repository.create(db, obj_in=complaint_data)

        # Queue outbox notification email
        notification_service.queue_notification(
            db,
            recipient=customer.user.email,
            subject=f"Complaint Filed - Category: {complaint_in.category.capitalize()}",
            body=f"Hello {customer.first_name},\n\nWe have received your complaint regarding the meal on {delivery_log.delivery_date}. Category: {complaint_in.category}. Summary: {complaint_in.description}. We will review it shortly."
        )

        return complaint

    def resolve_complaint(self, db: Session, complaint_id: UUID, resolution_in: ComplaintResolve) -> Complaint:
        """Resolve an open/escalated complaint and notify the customer of the resolution."""
        complaint = complaint_repository.get(db, id=complaint_id)
        if not complaint:
            raise EntityNotFoundException("Complaint not found.")

        # Update status and resolution notes
        resolved_complaint = complaint_repository.update(
            db,
            db_obj=complaint,
            obj_in={
                "status": "resolved",
                "resolution_notes": resolution_in.resolution_notes
            }
        )

        # Queue outbox notification email
        customer = resolved_complaint.customer
        notification_service.queue_notification(
            db,
            recipient=customer.user.email,
            subject="Complaint Resolved - Saanjh Ki Roti Support",
            body=f"Hello {customer.first_name},\n\nYour complaint #{str(complaint.id)[:8].upper()} has been resolved.\n\nResolution Notes: {resolution_in.resolution_notes}\n\nThank you for choosing Saanjh Ki Roti."
        )

        return resolved_complaint

    def escalate_complaints_task(self, db: Session) -> int:
        """Scan for open complaints older than 24 hours and escalate them to Tier 2 support."""
        escalated_count = 0
        old_complaints = complaint_repository.get_open_older_than(db, hours=24)

        for complaint in old_complaints:
            complaint_repository.update(db, db_obj=complaint, obj_in={"status": "escalated"})
            escalated_count += 1

            # Queue outbox email notification to customer
            customer = complaint.customer
            notification_service.queue_notification(
                db,
                recipient=customer.user.email,
                subject="Complaint Status Escalated - Tier 2 Support",
                body=f"Hello {customer.first_name},\n\nYour complaint #{str(complaint.id)[:8].upper()} has been escalated to Tier 2 support as it remained unresolved for 24 hours. Our support manager will contact you directly."
            )

        return escalated_count

# Global complaint service instance
complaint_service = ComplaintService()
