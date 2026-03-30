"""Inspect posting_skills distribution and sample keywords from job postings."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=== Skill extraction counts ===")
rows = db.execute(text("""
    SELECT s.name, COUNT(1) occurrences
    FROM posting_skills ps
    JOIN skills s ON s.id = ps.skill_id
    GROUP BY s.name
    ORDER BY occurrences DESC
""")).fetchall()
for r in rows:
    print(f"  {r[0]:<30} {r[1]}")

print()
print("=== Sample skills column values from DB ===")
samples = db.execute(text("""
    SELECT title, skills
    FROM job_postings_unified
    WHERE skills IS NOT NULL AND skills != ''
    LIMIT 15
""")).fetchall()
for r in samples:
    print(f"  [{r[0][:40]}] -> {r[1][:80]}")

db.close()
