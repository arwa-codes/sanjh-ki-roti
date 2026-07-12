import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, Date, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.session import Base

class BillingTransaction(Base):
    __tablename__ = "billing_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
    billing_date = Column(Date, nullable=False, default=datetime.utcnow().date)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    payment_status = Column(String, default="unpaid", nullable=False)  # paid | unpaid | failed
    gateway_transaction_id = Column(String, nullable=True)
    invoice_url = Column(String, nullable=True)

    # Relationships
    customer = relationship("Customer")
    subscription = relationship("Subscription")

class MealAddon(Base):
    __tablename__ = "meal_addons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    addon_date = Column(Date, nullable=False)
    meal_type = Column(String, nullable=False)  # lunch | dinner
    addon_type = Column(String, nullable=False)  # extra_roti | sweet | buttermilk
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Numeric(precision=10, scale=2), nullable=False)
    is_paid = Column(Boolean, default=False, nullable=False)

    # Relationships
    subscription = relationship("Subscription", backref="addons")

class Referral(Base):
    __tablename__ = "referrals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referrer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    referee_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    discount_applied = Column(Numeric(precision=10, scale=2), nullable=False, default=0.0)
    status = Column(String, default="pending", nullable=False)  # pending | claimed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    referrer = relationship("Customer", foreign_keys=[referrer_id], backref="referrals_made")
    referee = relationship("Customer", foreign_keys=[referee_id], backref="referrals_received")
