"""Inspect SDI snapshots and posting_skills distribution."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=== Top skills by posting count (global scope) ===")
rows = db.execute(text("""
    SELECT s.name, rc.name as role, ss.period, ss.sdi_value, ss.posting_count
    FROM sdi_snapshots ss
    JOIN skills s ON s.id = ss.skill_id
    JOIN role_catalog rc ON rc.id = ss.role_id
    WHERE ss.scope = 'global'
    ORDER BY ss.posting_count DESC
    LIMIT 20
""")).fetchall()
for r in rows:
    print(f"  {r[0]:<25} | {r[1]:<20} | {r[2]} | sdi={r[3]:.4f} | posts={r[4]}")

print()
print("=== Roles covered in SDI ===")
roles = db.execute(text("""
    SELECT rc.name, COUNT(DISTINCT ss.skill_id) skills, SUM(ss.posting_count) total_posts
    FROM sdi_snapshots ss
    JOIN role_catalog rc ON rc.id = ss.role_id
    WHERE ss.scope = 'global'
    GROUP BY rc.name
    ORDER BY total_posts DESC
""")).fetchall()
for r in roles:
    print(f"  {r[0]:<25} | skills={r[1]} | total_posts={r[2]}")

db.close()
