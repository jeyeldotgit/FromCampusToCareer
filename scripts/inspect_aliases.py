"""Inspect alias_map and show why some skills resolve but others don't."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

aliases = db.execute(text("SELECT alias, skill_id FROM skill_aliases LIMIT 30")).fetchall()
print(f"Total aliases: {db.execute(text('SELECT COUNT(1) FROM skill_aliases')).scalar()}")
print("Sample aliases:", [(r[0], str(r[1])[:8]) for r in aliases[:15]])

print()
# Show which extracted canonical names have no alias
from modules.taxonomy_admin.service import build_alias_map
alias_map = build_alias_map(db)
print(f"Alias map entries: {len(alias_map)}")
print("Sample alias_map keys:", list(alias_map.keys())[:15])

print()
# Which skills from the 50 are NOT in the alias_map?
skills = db.execute(text("SELECT id, name FROM skills")).fetchall()
missing = [s[1] for s in skills if s[1].lower() not in alias_map]
print(f"Skills NOT resolvable via alias_map ({len(missing)}):", missing[:20])
matched = [s[1] for s in skills if s[1].lower() in alias_map]
print(f"Skills resolvable via alias_map ({len(matched)}):", matched)

db.close()
