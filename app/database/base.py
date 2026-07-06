# Import all database models so that Base.metadata can auto-detect them for migrations
from app.database.session import Base
from app.models.user import User  # noqa
