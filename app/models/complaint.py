import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.session import Base

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    delivery_log_id = Column(UUID(as_uuid=True), ForeignKey("delivery_logs.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=False)  # "quality" | "quantity" | "delay" | "behavior"
    description = Column(String, nullable=False)
    status = Column(String, default="open", nullable=False)  # "open" | "in_progress" | "resolved" | "escalated"
    resolution_notes = Column(String, nullable=True)
    assigned_admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    customer = relationship("Customer")
    delivery_log = relationship("DeliveryLog")
    assigned_admin = relationship("User")
