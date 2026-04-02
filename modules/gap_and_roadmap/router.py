from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import require_student
from modules.analytics_sdi.service import get_weighted_sdi
from modules.auth.models import User
from modules.gap_and_roadmap.gap_service import compute_gap_analysis
from modules.gap_and_roadmap.models import ReadinessHistory
from modules.gap_and_roadmap.roadmap_service import build_roadmap
from modules.gap_and_roadmap.schemas import GapAnalysisResponse, ReadinessHistoryItem
from modules.student_profile.models import StudentProfile
from modules.student_profile.service import get_active_target_role

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/student", tags=["gap"])


@router.get("/gap-analysis", response_model=GapAnalysisResponse)
def get_gap_analysis(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_student)],
) -> GapAnalysisResponse:
    """Compute and return real-time gap analysis for the authenticated student.

    Runs synchronously against precomputed SDI snapshots. Gap results are
    persisted and readiness history is appended.
    """
    profile = db.query(StudentProfile).filter(
        StudentProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create a student profile first",
        )

    target = get_active_target_role(profile.id, db)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Declare a target role first",
        )

    weighted_sdi = get_weighted_sdi(role_id=target.role_id, db=db)

    # #region agent log — H-A post-fix: confirm scope fallback produced results
    import json as _json, time as _time
    from pathlib import Path as _Path
    _LOG_FILE = _Path(__file__).resolve().parents[3] / "debug-feaa13.log"
    with open(_LOG_FILE, "a") as _lf:
        _lf.write(_json.dumps({
            "sessionId": "feaa13", "runId": "post-fix", "hypothesisId": "H-A",
            "location": "gap_and_roadmap/router.py:get_weighted_sdi_result",
            "message": "weighted_sdi after scope-fallback fix",
            "data": {"role_id": str(target.role_id), "result_size": len(weighted_sdi), "is_empty": not weighted_sdi},
            "timestamp": int(_time.time() * 1000),
        }) + "\n")
    # #endregion

    if not weighted_sdi:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SDI data not yet computed. Ask an admin to run the pipeline.",
        )

    gaps, readiness = compute_gap_analysis(
        student_id=profile.id,
        role_id=target.role_id,
        weighted_sdi=weighted_sdi,
        db=db,
    )
    roadmap = build_roadmap(gaps)

    period = datetime.now(tz=timezone.utc).strftime("%Y-%m")
    db.add(
        ReadinessHistory(
            student_id=profile.id,
            role_id=target.role_id,
            period=period,
            readiness_score=readiness,
        )
    )
    db.commit()

    role_row = db.execute(
        text("SELECT name FROM role_catalog WHERE id = :rid"),
        {"rid": str(target.role_id)},
    ).first()
    role_name = role_row[0] if role_row else str(target.role_id)

    return GapAnalysisResponse(
        role_id=target.role_id,
        role_name=role_name,
        readiness_score=readiness,
        period=period,
        gaps=gaps,
        roadmap=roadmap,
    )


@router.get("/readiness-history", response_model=list[ReadinessHistoryItem])
def get_readiness_history(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_student)],
) -> list[ReadinessHistoryItem]:
    profile = db.query(StudentProfile).filter(
        StudentProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create a student profile first",
        )

    history = (
        db.query(ReadinessHistory)
        .filter(ReadinessHistory.student_id == profile.id)
        .order_by(ReadinessHistory.computed_at.desc())
        .all()
    )
    return [ReadinessHistoryItem.model_validate(h) for h in history]
