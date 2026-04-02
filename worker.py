"""Worker CLI entry point — Stage 1 manual invocation model.

Reads the oldest pending run from pipeline_runs, then executes:
    1. load_historical_batch  (ingestion)
    2. run_normalization      (skill extraction → posting_skills)
    3. run_sdi_refresh        (SDI snapshot computation)

Usage:
    python worker.py

No scheduler in Stage 1. This script is triggered manually by an admin
after POST /admin/jobs/run creates a pending row.
"""

from __future__ import annotations
from core.config import settings

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

csv_paths = [
    Path(settings.processed_data_path) / "unified_job_postings.csv",
    Path(settings.processed_data_path) / "ict_postings_2020_2025.csv",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    """Execute the full ETL pipeline chain against the oldest pending run.

    Marks the run as 'running' before execution and 'completed' or 'failed'
    after. If no pending run exists, logs a message and exits.
    """
    from core.database import SessionLocal
    from modules.analytics_sdi.service import run_sdi_refresh
    from modules.ingestion.loader import load_historical_batch
    from modules.ingestion.models import PipelineRun
    from modules.normalization.pipeline import run_normalization

    db = SessionLocal()
    try:
        run = (
            db.query(PipelineRun)
            .filter(PipelineRun.status == "pending")
            .order_by(PipelineRun.created_at.asc())
            .first()
        )
        if not run:
            logger.info("No pending pipeline runs found. Exiting.")
            return

        run.status = "running"
        run.started_at = datetime.now(tz=timezone.utc)
        db.commit()
        logger.info("Pipeline run started", extra={"run_id": str(run.id)})

        logger.info("Step 1/3: Loading historical batch...")
        processed_dir = Path(settings.processed_data_path)
        csv_paths = sorted(processed_dir.glob("*.csv"))

        if not csv_paths:
            raise RuntimeError(f"No CSV files found in {processed_dir}")

        logger.info("Found %d CSV file(s): %s", len(csv_paths), [p.name for p in csv_paths])

        total = {"inserted": 0, "skipped": 0, "quarantined": 0}
        for csv_path in csv_paths:
            logger.info("Loading %s...", csv_path.name)
            result = load_historical_batch(db, csv_paths=[csv_path])
            for k in total:
                total[k] += result[k]

        logger.info("Batch load: %s", total)

        logger.info("Step 2/3: Running normalization (skill extraction)...")
        norm_result = run_normalization(db)
        logger.info("Normalization: %s", norm_result)

        logger.info("Step 3/3: Computing SDI snapshots (global + ph)...")
        global_count = run_sdi_refresh(db, scope="global", country_filter=None)
        ph_count = run_sdi_refresh(db, scope="ph", country_filter="PH")
        sdi_count = global_count + ph_count
        logger.info("SDI snapshots upserted: %d (global=%d, ph=%d)", sdi_count, global_count, ph_count)

        run.status = "completed"
        run.finished_at = datetime.now(tz=timezone.utc)
        db.commit()
        logger.info("Pipeline run completed", extra={"run_id": str(run.id)})

    except Exception as exc:
        logger.error("Pipeline run failed", exc_info=True)
        if run:
            run.status = "failed"
            run.error_message = str(exc)
            run.finished_at = datetime.now(tz=timezone.utc)
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run_pipeline()
