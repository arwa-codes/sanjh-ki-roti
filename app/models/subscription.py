import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.session import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending | active | paused | expired | cancelled
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    remaining_meals = Column(Integer, nullable=False)
    original_price = Column(Numeric(precision=10, scale=2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    customer = relationship("Customer", backref="subscriptions")
    plan = relationship("Plan")
    delivery_logs = relationship("DeliveryLog", back_populates="subscription", cascade="all, delete-orphan")

class SubscriptionPause(Base):
    __tablename__ = "subscription_pauses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending | active | completed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    subscription = relationship("Subscription", backref="pauses")
