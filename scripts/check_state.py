"""Quick DB state check script."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
print("Skills:", db.execute(text("SELECT COUNT(1) FROM skills")).scalar())
cols = db.execute(text(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name='job_postings_unified' ORDER BY ordinal_position"
)).fetchall()
print("job_postings_unified columns:", [c[0] for c in cols])
print("posting_skills rows:", db.execute(text("SELECT COUNT(1) FROM posting_skills")).scalar())
print("sdi_snapshots rows:", db.execute(text("SELECT COUNT(1) FROM sdi_snapshots")).scalar())
db.close()
