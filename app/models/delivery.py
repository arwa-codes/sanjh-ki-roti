import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.session import Base

class Route(Base):
    __tablename__ = "routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    area = Column(String, nullable=False)
    pincodes = Column(String, nullable=False)  # JSON-encoded list of string pincodes
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    partners = relationship("DeliveryPartner", back_populates="route")
    delivery_logs = relationship("DeliveryLog", back_populates="route")

class DeliveryPartner(Base):
    __tablename__ = "delivery_partners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    dl_number = Column(String, unique=True, nullable=False)
    document_url = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    current_route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="delivery_profile")
    route = relationship("Route", back_populates="partners")
    delivery_logs = relationship("DeliveryLog", back_populates="delivery_partner")

class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    delivery_partner_id = Column(UUID(as_uuid=True), ForeignKey("delivery_partners.id", ondelete="SET NULL"), nullable=True)
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id", ondelete="SET NULL"), nullable=True)
    delivery_date = Column(Date, nullable=False)
    meal_type = Column(String, nullable=False)  # "lunch" | "dinner"
    status = Column(String, default="pending", nullable=False)  # "pending" | "out_for_delivery" | "delivered" | "failed"
    failure_reason = Column(String, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    photo_proof_url = Column(String, nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="delivery_logs")
    delivery_partner = relationship("DeliveryPartner", back_populates="delivery_logs")
    route = relationship("Route", back_populates="delivery_logs")
