from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.database.session import get_db
from app.schemas.complaint import ComplaintCreate, ComplaintResolve, ComplaintResponse
from app.services.complaint_service import complaint_service
from app.repositories.complaint import complaint_repository
from app.repositories.customer import customer_repository
from app.api.dependencies import get_current_user, RoleChecker
from app.models.user import User
from app.core.exceptions import ForbiddenException

router = APIRouter()

@router.post(
    "",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="File a new dispute complaint"
)
def file_complaint(
    complaint_in: ComplaintCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ComplaintResponse:
    """Log a complaint regarding a delivery run (Customer scope)."""
    if current_user.role != "customer":
        raise ForbiddenException("Only customers can file complaints.")
        
    profile = customer_repository.get_by_user_id(db, user_id=current_user.id)
    if not profile:
        raise ForbiddenException("Customer profile must be registered.")
        
    return complaint_service.create_complaint(db, customer_id=profile.id, complaint_in=complaint_in)

@router.get(
    "",
    response_model=List[ComplaintResponse],
    dependencies=[Depends(RoleChecker(["admin"]))],
    summary="List all complaints (Admin only)"
)
def list_complaints(db: Session = Depends(get_db)) -> List[ComplaintResponse]:
    """Retrieve all logged complaints (Admin scope)."""
    return complaint_repository.get_multi(db)

@router.patch(
    "/{complaint_id}/resolve",
    response_model=ComplaintResponse,
    dependencies=[Depends(RoleChecker(["admin"]))],
    summary="Resolve a customer complaint (Admin only)"
)
def resolve_complaint(
    complaint_id: UUID,
    resolution_in: ComplaintResolve,
    db: Session = Depends(get_db)
) -> ComplaintResponse:
    """Resolve an open complaint and log support feedback (Admin scope)."""
    return complaint_service.resolve_complaint(db, complaint_id=complaint_id, resolution_in=resolution_in)

@router.post(
    "/escalate-sla",
    dependencies=[Depends(RoleChecker(["admin"]))],
    summary="Trigger SLA escalation check (Admin only)"
)
def trigger_escalation_check(db: Session = Depends(get_db)) -> dict:
    """Manually execute complaint SLA scans to escalate 24hr open disputes (Admin scope)."""
    escalated_count = complaint_service.escalate_complaints_task(db)
    return {
        "status": "success",
        "message": f"SLA escalation scan complete. Escalated {escalated_count} complaints."
    }
