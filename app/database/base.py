# Import all database models so that Base.metadata can auto-detect them for migrations
from app.database.session import Base
from app.models.user import User  # noqa
from app.models.customer import Customer  # noqa
from app.models.plan import Plan  # noqa
from app.models.subscription import Subscription, SubscriptionPause  # noqa
from app.models.billing import BillingTransaction, MealAddon, Referral  # noqa

