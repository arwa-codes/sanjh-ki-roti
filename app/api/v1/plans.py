from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.database.session import get_db
from app.schemas.plan import PlanCreate, PlanUpdate, PlanResponse
from app.repositories.plan import plan_repository
from app.api.dependencies import get_current_user, RoleChecker
from app.core.exceptions import EntityNotFoundException, EntityAlreadyExistsException

router = APIRouter()

@router.post(
    "",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["admin"]))],
    summary="Create a new subscription plan (Admin only)"
)
def create_plan(plan_in: PlanCreate, db: Session = Depends(get_db)) -> PlanResponse:
    """Create a new subscription plan for customers (Admin only)."""
    if plan_repository.get_by_name(db, name=plan_in.name):
        raise EntityAlreadyExistsException("A plan with this name already exists.")
        
    plan_data = plan_in.model_dump()
    return plan_repository.create(db, obj_in=plan_data)

@router.get(
    "",
    response_model=List[PlanResponse],
    summary="List active subscription plans"
)
def list_plans(db: Session = Depends(get_db)) -> List[PlanResponse]:
    """Retrieve all available subscription plans."""
    return plan_repository.get_active_plans(db)

@router.get(
    "/{plan_id}",
    response_model=PlanResponse,
    summary="Retrieve subscription plan details"
)
def get_plan(plan_id: UUID, db: Session = Depends(get_db)) -> PlanResponse:
    """Fetch plan information by ID."""
    plan = plan_repository.get(db, id=plan_id)
    if not plan:
        raise EntityNotFoundException("Subscription plan not found.")
    return plan

@router.patch(
    "/{plan_id}",
    response_model=PlanResponse,
    dependencies=[Depends(RoleChecker(["admin"]))],
    summary="Update subscription plan details (Admin only)"
)
def update_plan(
    plan_id: UUID,
    plan_in: PlanUpdate,
    db: Session = Depends(get_db)
) -> PlanResponse:
    """Modify subscription plan configurations (Admin only)."""
    plan = plan_repository.get(db, id=plan_id)
    if not plan:
        raise EntityNotFoundException("Subscription plan not found.")
        
    update_data = plan_in.model_dump(exclude_unset=True)
    return plan_repository.update(db, db_obj=plan, obj_in=update_data)
