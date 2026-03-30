from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import decode_access_token

_bearer = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> object:
    """Validate Bearer token and return the authenticated User.

    Args:
        credentials: Authorization header parsed by HTTPBearer.
        db: Active database session.

    Returns:
        The authenticated User ORM instance.

    Raises:
        HTTPException 401: If the token is missing, invalid, or expired.
    """
    # Import here to avoid circular dependency at module load time
    from modules.auth.models import User

    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise exc
    except JWTError:
        raise exc

    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if user is None:
        raise exc
    return user


def require_student(
    current_user: Annotated[object, Depends(get_current_user)],
) -> object:
    """Dependency that restricts access to student-role users.

    Raises:
        HTTPException 403: If the authenticated user is not a student.
    """
    from modules.auth.models import User

    user: User = current_user  # type: ignore[assignment]
    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students only",
        )
    return user


def require_admin(
    current_user: Annotated[object, Depends(get_current_user)],
) -> object:
    """Dependency that restricts access to admin-role users.

    Raises:
        HTTPException 403: If the authenticated user is not an admin.
    """
    from modules.auth.models import User

    user: User = current_user  # type: ignore[assignment]
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins only",
        )
    return user
