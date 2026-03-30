from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import require_admin
from modules.ingestion.models import PipelineRun
from modules.ingestion.schemas import PipelineRunResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/jobs/run",
    response_model=PipelineRunResponse,
    status_code=202,
    dependencies=[Depends(require_admin)],
)
def trigger_pipeline(
    db: Annotated[Session, Depends(get_db)],
) -> PipelineRunResponse:
    """Create a pending pipeline run row.

    The admin must then run `python worker.py` to execute the pipeline.
    Returns the newly created run record immediately (202 Accepted).
    """
    run = PipelineRun(status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)
    return PipelineRunResponse.model_validate(run)


@router.get(
    "/pipeline-runs",
    response_model=list[PipelineRunResponse],
    dependencies=[Depends(require_admin)],
)
def list_pipeline_runs(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[PipelineRunResponse]:
    """Return recent pipeline runs ordered by creation date descending.

    Args:
        limit: Maximum number of runs to return (1–100, default 20).
    """
    runs = (
        db.query(PipelineRun)
        .order_by(PipelineRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [PipelineRunResponse.model_validate(r) for r in runs]
