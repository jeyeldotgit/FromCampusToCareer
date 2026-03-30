from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, field_validator

VALID_DEPTH_LEVELS = {"Advanced", "Proficient", "Intermediate", "Foundational"}


class SkillCreate(BaseModel):
    name: str
    description: str | None = None


class SkillResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class AliasCreate(BaseModel):
    alias: str
    skill_id: uuid.UUID


class AliasResponse(BaseModel):
    id: uuid.UUID
    alias: str
    skill_id: uuid.UUID

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class CourseMappingCreate(BaseModel):
    course_code: str
    skill_id: uuid.UUID
    min_depth: str

    @field_validator("min_depth")
    @classmethod
    def validate_depth(cls, v: str) -> str:
        if v not in VALID_DEPTH_LEVELS:
            raise ValueError(f"min_depth must be one of {VALID_DEPTH_LEVELS}")
        return v


class CourseMappingResponse(BaseModel):
    id: uuid.UUID
    course_code: str
    skill_id: uuid.UUID
    min_depth: str

    model_config = {"from_attributes": True}


class GradeDepthRuleCreate(BaseModel):
    min_grade: Decimal
    max_grade: Decimal
    depth_level: str

    @field_validator("depth_level")
    @classmethod
    def validate_depth(cls, v: str) -> str:
        if v not in VALID_DEPTH_LEVELS:
            raise ValueError(f"depth_level must be one of {VALID_DEPTH_LEVELS}")
        return v


class GradeDepthRuleResponse(BaseModel):
    id: uuid.UUID
    min_grade: Decimal
    max_grade: Decimal
    depth_level: str

    model_config = {"from_attributes": True}
