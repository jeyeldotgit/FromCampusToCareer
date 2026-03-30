from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import require_admin
from modules.taxonomy_admin.schemas import (
    AliasCreate,
    AliasResponse,
    CourseMappingCreate,
    CourseMappingResponse,
    GradeDepthRuleCreate,
    GradeDepthRuleResponse,
    RoleCreate,
    RoleResponse,
    SkillCreate,
    SkillResponse,
)
from modules.taxonomy_admin.service import (
    build_alias_map,
    create_alias,
    create_course_mapping,
    create_role,
    create_skill,
    list_roles,
    list_skills,
    upsert_grade_depth_rule,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/skills",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def add_skill(
    payload: SkillCreate,
    db: Annotated[Session, Depends(get_db)],
) -> SkillResponse:
    skill = create_skill(payload, db)
    return SkillResponse.model_validate(skill)


@router.get(
    "/skills",
    response_model=list[SkillResponse],
    dependencies=[Depends(require_admin)],
)
def get_skills(db: Annotated[Session, Depends(get_db)]) -> list[SkillResponse]:
    return [SkillResponse.model_validate(s) for s in list_skills(db)]


@router.post(
    "/aliases",
    response_model=AliasResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def add_alias(
    payload: AliasCreate,
    db: Annotated[Session, Depends(get_db)],
) -> AliasResponse:
    alias = create_alias(payload, db)
    return AliasResponse.model_validate(alias)


@router.get(
    "/roles",
    response_model=list[RoleResponse],
)
def get_roles(db: Annotated[Session, Depends(get_db)]) -> list[RoleResponse]:
    """Public endpoint: returns active roles for the student role-selection UI."""
    return [RoleResponse.model_validate(r) for r in list_roles(db)]


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def add_role(
    payload: RoleCreate,
    db: Annotated[Session, Depends(get_db)],
) -> RoleResponse:
    role = create_role(payload, db)
    return RoleResponse.model_validate(role)


@router.post(
    "/course-skill-mappings",
    response_model=CourseMappingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def add_course_mapping(
    payload: CourseMappingCreate,
    db: Annotated[Session, Depends(get_db)],
) -> CourseMappingResponse:
    mapping = create_course_mapping(payload, db)
    return CourseMappingResponse.model_validate(mapping)


@router.post(
    "/grade-depth-rules",
    response_model=GradeDepthRuleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def add_grade_depth_rule(
    payload: GradeDepthRuleCreate,
    db: Annotated[Session, Depends(get_db)],
) -> GradeDepthRuleResponse:
    rule = upsert_grade_depth_rule(payload, db)
    return GradeDepthRuleResponse.model_validate(rule)
