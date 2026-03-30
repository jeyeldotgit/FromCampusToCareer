"""One-time migration: add skills TEXT column to job_postings_unified."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE job_postings_unified ADD COLUMN IF NOT EXISTS skills TEXT"
    ))
    conn.commit()
    print("Migration complete: skills column added to job_postings_unified")
