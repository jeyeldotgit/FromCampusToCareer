from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_validator

VALID_PROGRAMS = {"BSIT", "BSCS", "BSIS"}
VALID_SEMESTERS = {"1st", "2nd", "summer"}


class CourseRecordIn(BaseModel):
    course_code: str
    course_name: str
    grade: Decimal
    academic_year: str
    semester: str

    @field_validator("semester")
    @classmethod
    def validate_semester(cls, v: str) -> str:
        if v not in VALID_SEMESTERS:
            raise ValueError(f"semester must be one of {VALID_SEMESTERS}")
        return v

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, v: Decimal) -> Decimal:
        if not (Decimal("1.00") <= v <= Decimal("5.00")):
            raise ValueError("grade must be between 1.00 and 5.00")
        return v


class CertificationIn(BaseModel):
    name: str
    issuer: str
    issued_date: date | None = None
    credential_url: str | None = None


class ProjectIn(BaseModel):
    title: str
    description: str | None = None
    tech_stack: str | None = None
    project_url: str | None = None


class ProfileCreateRequest(BaseModel):
    year_level: int
    program: str
    university: str | None = None
    courses: list[CourseRecordIn] = []
    certifications: list[CertificationIn] = []
    projects: list[ProjectIn] = []

    @field_validator("program")
    @classmethod
    def validate_program(cls, v: str) -> str:
        if v not in VALID_PROGRAMS:
            raise ValueError(f"program must be one of {VALID_PROGRAMS}")
        return v

    @field_validator("year_level")
    @classmethod
    def validate_year(cls, v: int) -> int:
        if not (1 <= v <= 5):
            raise ValueError("year_level must be between 1 and 5")
        return v


class TargetRoleRequest(BaseModel):
    role_id: uuid.UUID


class CourseRecordResponse(BaseModel):
    id: uuid.UUID
    course_code: str
    course_name: str
    grade: Decimal
    academic_year: str
    semester: str

    model_config = {"from_attributes": True}


class ProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    year_level: int
    program: str
    university: str | None
    courses: list[CourseRecordResponse] = []

    model_config = {"from_attributes": True}
