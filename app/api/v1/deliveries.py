from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from app.database.session import get_db
from app.schemas.delivery import RouteCreate, RouteResponse, DeliveryPartnerCreate, DeliveryPartnerResponse, DeliveryLogResponse, DeliveryLogStatusUpdate
from app.services.delivery_service import delivery_service
from app.repositories.delivery import route_repository, delivery_partner_repository, delivery_log_repository
from app.api.dependencies import get_current_user, RoleChecker
from app.models.user import User
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.services.subscription_service import get_ist_now

router = APIRouter()

@router.post(
    "/routes",
    response_model=RouteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["admin"]))],
    summary="Create a new delivery route (Admin only)"
)
def create_route(route_in: RouteCreate, db: Session = Depends(get_db)) -> RouteResponse:
    """Register a new active logistics delivery route."""
    return delivery_service.create_route(db, route_in=route_in)

@router.get(
    "/routes",
    response_model=List[RouteResponse],
    summary="List all routes"
)
def list_routes(db: Session = Depends(get_db)) -> List[RouteResponse]:
    """Retrieve all defined logistics routes."""
    return route_repository.get_multi(db)

@router.post(
    "/partners",
    response_model=DeliveryPartnerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register delivery partner profile"
)
def register_partner(
    partner_in: DeliveryPartnerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DeliveryPartnerResponse:
    """Create a profile for the currently logged-in delivery user."""
    if current_user.role != "delivery":
        raise ForbiddenException("Only users with role 'delivery' can register a partner profile.")
    return delivery_service.create_delivery_partner(db, user_id=current_user.id, partner_in=partner_in)

@router.get(
    "/partners/me",
    response_model=DeliveryPartnerResponse,
    summary="Retrieve current partner profile"
)
def get_partner_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DeliveryPartnerResponse:
    """Fetch the delivery partner profile details for the logged-in user."""
    partner = delivery_partner_repository.get_by_user_id(db, user_id=current_user.id)
    if not partner:
        raise EntityNotFoundException("Delivery partner profile not found.")
    return partner

@router.post(
    "/partners/upload-dl",
    summary="Upload Driving License document"
)
async def upload_dl(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Upload DL verification document for the current delivery partner."""
    partner = delivery_partner_repository.get_by_user_id(db, user_id=current_user.id)
    if not partner:
        raise EntityNotFoundException("Delivery partner profile not found.")
        
    contents = await file.read()
    mock_url = delivery_service.upload_dl_document(
        db, partner_id=partner.id, file_content=contents, filename=file.filename
    )
    return {"document_url": mock_url}

@router.patch(
    "/partners/{partner_id}/verify",
    response_model=DeliveryPartnerResponse,
    dependencies=[Depends(RoleChecker(["admin"]))],
    summary="Verify delivery partner (Admin only)"
)
def verify_partner(
    partner_id: UUID,
    is_verified: bool,
    db: Session = Depends(get_db)
) -> DeliveryPartnerResponse:
    """Approve or reject a delivery partner's verification profile (Admin scope)."""
    return delivery_service.verify_partner(db, partner_id=partner_id, is_verified=is_verified)

@router.patch(
    "/partners/{partner_id}/assign-route",
    response_model=DeliveryPartnerResponse,
    dependencies=[Depends(RoleChecker(["admin"]))],
    summary="Assign route to partner (Admin only)"
)
def assign_route(
    partner_id: UUID,
    route_id: UUID,
    db: Session = Depends(get_db)
) -> DeliveryPartnerResponse:
    """Bind a delivery partner to a specific active logistics route (Admin scope)."""
    return delivery_service.assign_route(db, partner_id=partner_id, route_id=route_id)

@router.post(
    "/generate-run",
    response_model=List[DeliveryLogResponse],
    dependencies=[Depends(RoleChecker(["admin"]))],
    summary="Trigger daily delivery runs (Admin only)"
)
def trigger_delivery_run(
    delivery_date: date = Query(..., description="Target run date (YYYY-MM-DD)"),
    meal_type: str = Query(..., pattern=r"^(lunch|dinner)$", description="Target meal type (lunch or dinner)"),
    db: Session = Depends(get_db)
) -> List[DeliveryLogResponse]:
    """Execute logistics logic to compile active tiffin runs and assign drivers."""
    return delivery_service.generate_daily_delivery_logs(db, delivery_date=delivery_date, meal_type=meal_type)

@router.get(
    "/daily",
    response_model=List[DeliveryLogResponse],
    summary="Retrieve daily route sheet runs"
)
def list_daily_runs(
    delivery_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[DeliveryLogResponse]:
    """Fetch daily scheduled delivery logs. Drivers view assigned; Admins view all."""
    target_date = delivery_date or get_ist_now().date()
    
    if current_user.role == "admin":
        return db.query(delivery_log_repository.model).filter(
            delivery_log_repository.model.delivery_date == target_date
        ).all()
        
    if current_user.role == "delivery":
        partner = delivery_partner_repository.get_by_user_id(db, user_id=current_user.id)
        if not partner:
            raise ForbiddenException("Delivery partner profile must be registered.")
        return delivery_log_repository.get_route_sheet_for_partner(
            db, partner_id=partner.id, delivery_date=target_date
        )
        
    raise ForbiddenException("Access denied.")

@router.patch(
    "/{log_id}/status",
    response_model=DeliveryLogResponse,
    summary="Update delivery status"
)
def update_run_status(
    log_id: UUID,
    status_in: DeliveryLogStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DeliveryLogResponse:
    """Mark progress status of a scheduled delivery run (out_for_delivery/delivered/failed)."""
    # Enforce role protection: only assigned driver or admin can update status
    log = delivery_log_repository.get(db, id=log_id)
    if not log:
        raise EntityNotFoundException("Delivery log not found.")
        
    if current_user.role != "admin":
        partner = delivery_partner_repository.get_by_user_id(db, user_id=current_user.id)
        if not partner or log.delivery_partner_id != partner.id:
            raise ForbiddenException("You are not authorized to update this delivery status.")
            
    return delivery_service.update_delivery_status(db, log_id=log_id, status_in=status_in)
