import uuid
from sqlalchemy import Column, String, Integer, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database.session import Base

class Plan(Base):
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    duration_days = Column(Integer, nullable=False)
    price = Column(Numeric(precision=10, scale=2), nullable=False)
    meals_included = Column(String, default="both", nullable=False)  # lunch | dinner | both
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Plan name={self.name} price={self.price}>"
