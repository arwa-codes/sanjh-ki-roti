from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, Token
from app.repositories.user import user_repository
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import AuthenticationException, EntityAlreadyExistsException

class AuthService:
    def register_user(self, db: Session, user_in: UserCreate) -> User:
        """Register a new customer, delivery agent, or admin."""
        # Enforce unique email check
        if user_repository.get_by_email(db, email=user_in.email):
            raise EntityAlreadyExistsException("A user with this email address already exists.")
        
        # Enforce unique phone number check
        if user_repository.get_by_phone(db, phone=user_in.phone):
            raise EntityAlreadyExistsException("A user with this phone number already exists.")
        
        hashed_password = get_password_hash(user_in.password)
        user_data = {
            "email": user_in.email,
            "phone": user_in.phone,
            "hashed_password": hashed_password,
            "role": user_in.role,
            "is_active": True
        }
        return user_repository.create(db, obj_in=user_data)

    def authenticate_user(self, db: Session, email: str, password: str) -> User:
        """Authenticate user credentials and return the user if valid."""
        user = user_repository.get_by_email(db, email=email)
        if not user:
            raise AuthenticationException("Incorrect email or password.")
        
        if not verify_password(password, user.hashed_password):
            raise AuthenticationException("Incorrect email or password.")
            
        if not user.is_active:
            raise AuthenticationException("User account is deactivated.")
            
        return user

    def create_user_token(self, user: User) -> Token:
        """Generate a JWT token for the authenticated user."""
        token_payload = {
            "sub": str(user.id),
            "role": user.role
        }
        access_token = create_access_token(data=token_payload)
        return Token(access_token=access_token, token_type="bearer")

# Global authentication service instance
auth_service = AuthService()
