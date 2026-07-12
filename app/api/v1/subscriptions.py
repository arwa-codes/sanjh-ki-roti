from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.database.session import get_db
from app.schemas.subscription import SubscriptionCreate, SubscriptionResponse, SubscriptionPauseCreate, SubscriptionPauseResponse
from app.schemas.billing import MealAddonCreate, MealAddonResponse
from app.services.subscription_service import subscription_service
from app.repositories.subscription import subscription_repository, subscription_pause_repository
from app.repositories.customer import customer_repository
from app.api.dependencies import get_current_user
from app.models.user import User
from app.core.exceptions import EntityNotFoundException, ForbiddenException

router = APIRouter()

def _get_customer_profile(db: Session, user: User):
    """Utility to retrieve customer profile for user, checking that it exists."""
    profile = customer_repository.get_by_user_id(db, user_id=user.id)
    if not profile:
        raise ForbiddenException("Customer profile must be created before purchasing subscriptions.")
    return profile

@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to a plan"
)
def create_subscription(
    sub_in: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SubscriptionResponse:
    """Subscribe to a tiffin plan, creating an unpaid transaction invoice."""
    profile = _get_customer_profile(db, current_user)
    return subscription_service.purchase_subscription(db, customer_id=profile.id, plan_id=sub_in.plan_id)

@router.get(
    "",
    response_model=List[SubscriptionResponse],
    summary="List customer subscriptions"
)
def list_my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[SubscriptionResponse]:
    """Retrieve all subscriptions owned by the logged-in customer."""
    profile = _get_customer_profile(db, current_user)
    return subscription_repository.get_by_customer_id(db, customer_id=profile.id)

@router.post(
    "/{sub_id}/pause",
    response_model=SubscriptionPauseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Pause a subscription"
)
def pause_subscription(
    sub_id: UUID,
    pause_in: SubscriptionPauseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SubscriptionPauseResponse:
    """Schedule a pause period for an active subscription, validating cutoff times."""
    profile = _get_customer_profile(db, current_user)
    subscription = subscription_repository.get(db, id=sub_id)
    if not subscription or subscription.customer_id != profile.id:
        raise EntityNotFoundException("Subscription not found.")
        
    return subscription_service.pause_subscription(db, subscription_id=sub_id, pause_in=pause_in)

@router.post(
    "/{sub_id}/resume",
    response_model=SubscriptionResponse,
    summary="Resume a paused subscription early"
)
def resume_subscription(
    sub_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SubscriptionResponse:
    """End a pause interval early and resume meal deliveries."""
    profile = _get_customer_profile(db, current_user)
    subscription = subscription_repository.get(db, id=sub_id)
    if not subscription or subscription.customer_id != profile.id:
        raise EntityNotFoundException("Subscription not found.")
        
    return subscription_service.resume_subscription(db, subscription_id=sub_id)

@router.post(
    "/{sub_id}/addons",
    response_model=MealAddonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request a meal add-on"
)
def request_addon(
    sub_id: UUID,
    addon_in: MealAddonCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> MealAddonResponse:
    """Order daily add-on items (e.g., extra roti, sweet, buttermilk) for a meal."""
    profile = _get_customer_profile(db, current_user)
    subscription = subscription_repository.get(db, id=sub_id)
    if not subscription or subscription.customer_id != profile.id:
        raise EntityNotFoundException("Subscription not found.")
        
    return subscription_service.request_addon(db, subscription_id=sub_id, addon_in=addon_in)

@router.get(
    "/{sub_id}/pauses",
    response_model=List[SubscriptionPauseResponse],
    summary="List subscription pauses"
)
def list_pauses(
    sub_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[SubscriptionPauseResponse]:
    """Retrieve all pause records associated with a subscription."""
    profile = _get_customer_profile(db, current_user)
    subscription = subscription_repository.get(db, id=sub_id)
    if not subscription or subscription.customer_id != profile.id:
        raise EntityNotFoundException("Subscription not found.")
        
    return subscription_pause_repository.get_by_subscription_id(db, subscription_id=sub_id)
