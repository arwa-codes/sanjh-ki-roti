import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.session import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    pincode = Column(String, nullable=False)
    route_id = Column(UUID(as_uuid=True), nullable=True)  # Links to routes (Phase 3)
    aadhaar_number = Column(String, unique=True, nullable=False)
    document_url = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    referral_code = Column(String, unique=True, nullable=False)
    referred_by_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="customer", uselist=False)
    
    # We will define self-referencing relationship for referrals
    referred_by = relationship("Customer", remote_side=[id], backref="referees")

# Modify User model to link back to Customer
# Since User is in app/models/user.py, we will modify it later, or import and resolve
