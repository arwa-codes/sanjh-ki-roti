from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.database.session import get_db
from app.schemas.customer import CustomerCreate, CustomerResponse
from app.services.customer_service import customer_service
from app.api.dependencies import get_current_user, RoleChecker
from app.models.user import User

router = APIRouter()

@router.post(
    "/profile",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create customer profile"
)
def create_profile(
    customer_in: CustomerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CustomerResponse:
    """Create a profile for the currently logged-in customer user."""
    return customer_service.create_customer_profile(
        db, user_id=current_user.id, customer_in=customer_in
    )

@router.get(
    "/profile",
    response_model=CustomerResponse,
    summary="Retrieve current user profile"
)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CustomerResponse:
    """Fetch the profile details of the currently logged-in customer."""
    from app.repositories.customer import customer_repository
    from app.core.exceptions import EntityNotFoundException
    
    profile = customer_repository.get_by_user_id(db, user_id=current_user.id)
    if not profile:
        raise EntityNotFoundException("Customer profile not found.")
    return profile

@router.post(
    "/profile/upload-aadhaar",
    summary="Upload customer Aadhaar document"
)
async def upload_aadhaar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Upload Aadhaar verification document for the current customer."""
    from app.repositories.customer import customer_repository
    from app.core.exceptions import EntityNotFoundException

    profile = customer_repository.get_by_user_id(db, user_id=current_user.id)
    if not profile:
        raise EntityNotFoundException("Customer profile not found.")
        
    contents = await file.read()
    mock_url = customer_service.upload_aadhaar_document(
        db, customer_id=profile.id, file_content=contents, filename=file.filename
    )
    return {"document_url": mock_url}

@router.patch(
    "/profile/{customer_id}/verify",
    response_model=CustomerResponse,
    dependencies=[Depends(RoleChecker(["admin"]))],
    summary="Verify customer profile (Admin only)"
)
def verify_customer(
    customer_id: UUID,
    is_verified: bool,
    db: Session = Depends(get_db)
) -> CustomerResponse:
    """Approve or reject a customer's verification documents (Admin scope)."""
    return customer_service.verify_customer(db, customer_id=customer_id, is_verified=is_verified)
