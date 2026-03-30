"""Reset posting_skills and sdi_snapshots, then create a fresh pending pipeline run."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import SessionLocal, engine
from sqlalchemy import text
from modules.ingestion.models import PipelineRun

with engine.connect() as conn:
    conn.execute(text("DELETE FROM sdi_snapshots"))
    conn.execute(text("DELETE FROM posting_skills"))
    conn.commit()
    print("Cleared posting_skills and sdi_snapshots")

db = SessionLocal()
run = PipelineRun(status="pending")
db.add(run)
db.commit()
print("Created pending run:", run.id)
db.close()
