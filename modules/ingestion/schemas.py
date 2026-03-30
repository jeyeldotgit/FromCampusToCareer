from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class PipelineRunResponse(BaseModel):
    id: uuid.UUID
    status: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}


class PipelineRunResult(BaseModel):
    run_id: uuid.UUID
    status: str
    inserted: int | None = None
    normalized: int | None = None
    sdi_snapshots: int | None = None
    error: str | None = None
