from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from modules.student_profile.models import (
    Certification,
    CourseRecord,
    Project,
    StudentProfile,
    StudentTargetRole,
)
from modules.student_profile.schemas import ProfileCreateRequest, TargetRoleRequest

logger = logging.getLogger(__name__)


def get_or_create_profile(
    user_id: uuid.UUID,
    payload: ProfileCreateRequest,
    db: Session,
) -> StudentProfile:
    """Create or fully replace the student's academic profile.

    Existing course records, certifications, and projects are replaced when
    the profile is updated. Target roles are not touched by this operation.

    Args:
        user_id: UUID of the authenticated student user.
        payload: Profile data including courses, certifications, and projects.
        db: Active database session.

    Returns:
        The upserted StudentProfile instance.
    """
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()

    if profile:
        profile.year_level = payload.year_level
        profile.program = payload.program
        profile.university = payload.university
        # Replace child records completely on update
        for record in list(profile.course_records):
            db.delete(record)
        for cert in list(profile.certifications):
            db.delete(cert)
        for proj in list(profile.projects):
            db.delete(proj)
        db.flush()
    else:
        profile = StudentProfile(
            user_id=user_id,
            year_level=payload.year_level,
            program=payload.program,
            university=payload.university,
        )
        db.add(profile)
        db.flush()

    for course in payload.courses:
        db.add(CourseRecord(student_id=profile.id, **course.model_dump()))

    for cert in payload.certifications:
        db.add(Certification(student_id=profile.id, **cert.model_dump()))

    for proj in payload.projects:
        db.add(Project(student_id=profile.id, **proj.model_dump()))

    db.commit()
    db.refresh(profile)
    logger.info(
        "Profile upserted",
        extra={"student_id": str(profile.id), "user_id": str(user_id)},
    )
    return profile


def set_target_role(
    user_id: uuid.UUID,
    payload: TargetRoleRequest,
    db: Session,
) -> StudentTargetRole:
    """Set the student's active target role, deactivating previous selections.

    Args:
        user_id: UUID of the authenticated student user.
        payload: Contains the role_id to set as active.
        db: Active database session.

    Returns:
        The newly activated StudentTargetRole instance.
    """
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
    if not profile:
        raise ValueError("Student profile not found. Create a profile first.")

    db.query(StudentTargetRole).filter(
        StudentTargetRole.student_id == profile.id,
        StudentTargetRole.is_active.is_(True),
    ).update({"is_active": False})

    target = StudentTargetRole(
        student_id=profile.id,
        role_id=payload.role_id,
        is_active=True,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    logger.info(
        "Target role set",
        extra={"student_id": str(profile.id), "role_id": str(payload.role_id)},
    )
    return target


def get_active_target_role(
    student_id: uuid.UUID, db: Session
) -> StudentTargetRole | None:
    """Return the currently active target role for a student, or None.

    Args:
        student_id: UUID of the StudentProfile.
        db: Active database session.

    Returns:
        Active StudentTargetRole or None if no role is declared.
    """
    return (
        db.query(StudentTargetRole)
        .filter(
            StudentTargetRole.student_id == student_id,
            StudentTargetRole.is_active.is_(True),
        )
        .first()
    )
