from typing import List
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt
from app.core.config import settings
from app.core.exceptions import AuthenticationException, ForbiddenException
from app.database.session import get_db
from app.models.user import User
from app.repositories.user import user_repository

# Standard OAuth2 Password Bearer flow pointing to token generation endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Validate access token and return the currently authenticated user."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise AuthenticationException("Could not validate credentials")
        import uuid
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise AuthenticationException("Could not validate credentials")
    except jwt.PyJWTError:
        raise AuthenticationException("Could not validate credentials")
        
    user = user_repository.get(db, id=user_uuid)
    if not user:
        raise AuthenticationException("User not found")
        
    if not user.is_active:
        raise AuthenticationException("Inactive user account")
        
    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]) -> None:
        """Role-Based Access Control checker dependency."""
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """Enforce role permissions on the active endpoint."""
        if current_user.role not in self.allowed_roles:
            raise ForbiddenException("You do not have access to this resource.")
        return current_user
