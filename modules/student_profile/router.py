from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import require_student
from modules.auth.models import User
from modules.student_profile.schemas import (
    ProfileCreateRequest,
    ProfileResponse,
    TargetRoleRequest,
)
from modules.student_profile.service import (
    get_or_create_profile,
    set_target_role,
)

router = APIRouter(prefix="/student", tags=["student"])


@router.post(
    "/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_profile(
    payload: ProfileCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_student)],
) -> ProfileResponse:
    profile = get_or_create_profile(current_user.id, payload, db)
    return ProfileResponse.model_validate(profile)


@router.put("/profile", response_model=ProfileResponse)
def update_profile(
    payload: ProfileCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_student)],
) -> ProfileResponse:
    profile = get_or_create_profile(current_user.id, payload, db)
    return ProfileResponse.model_validate(profile)


@router.post(
    "/target-role",
    status_code=status.HTTP_200_OK,
)
def set_role(
    payload: TargetRoleRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_student)],
) -> dict[str, str]:
    try:
        target = set_target_role(current_user.id, payload, db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"role_id": str(target.role_id), "status": "active"}
