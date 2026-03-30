from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from core.security import create_access_token, hash_password, verify_password
from modules.auth.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from modules.auth.models import User
from modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse

logger = logging.getLogger(__name__)


def register_user(payload: RegisterRequest, db: Session) -> User:
    """Register a new user account.

    Args:
        payload: Registration data including email, password, full_name, and role.
        db: Active database session.

    Returns:
        The newly created User instance.

    Raises:
        EmailAlreadyRegisteredError: If the email is already in use.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise EmailAlreadyRegisteredError(payload.email)

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User registered", extra={"user_id": str(user.id), "role": user.role})
    return user


def login_user(payload: LoginRequest, db: Session) -> TokenResponse:
    """Authenticate a user and issue a JWT access token.

    Args:
        payload: Login credentials.
        db: Active database session.

    Returns:
        TokenResponse containing the access token, user_id, and role.

    Raises:
        InvalidCredentialsError: If credentials do not match any user.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise InvalidCredentialsError("Invalid email or password")

    token = create_access_token(subject=user.id, role=user.role)
    logger.info("User logged in", extra={"user_id": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)
