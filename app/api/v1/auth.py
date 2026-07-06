from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.auth_service import auth_service
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account"
)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    """Create a new user account (Customer, Delivery agent, or Admin)."""
    return auth_service.register_user(db, user_in=user_in)

@router.post(
    "/login",
    response_model=Token,
    summary="Generate access token via password authentication"
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Token:
    """Authenticate user credentials using form username (email) and password."""
    user = auth_service.authenticate_user(
        db,
        email=form_data.username,
        password=form_data.password
    )
    return auth_service.create_user_token(user)

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve current user profile info"
)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Fetch profile data of the currently logged-in user."""
    return current_user
