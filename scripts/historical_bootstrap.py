"""One-time historical dataset bootstrap script.

Reads the five Kaggle source datasets, applies the tech-field filter,
maps raw titles to canonical roles, generates deterministic posting_ids,
deduplicates, and writes data/processed/unified_job_postings.csv.

This script is a prerequisite for worker.py. Run it once before triggering
the first pipeline run via POST /admin/jobs/run.

Usage (from backend/ directory):
    python scripts/historical_bootstrap.py

    # Dry run — prints stats without writing output:
    python scripts/historical_bootstrap.py --dry-run

    # Custom output path:
    python scripts/historical_bootstrap.py --output data/processed/custom.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure backend/ is on sys.path so module imports resolve correctly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from core.config import settings
from core.posting_id import make_posting_id
from modules.ingestion.transformers import CANONICAL_COLUMNS
from modules.ingestion.transformers.tech_filter import filter_tech_jobs
from modules.ingestion.transformers.role_mapping import map_role, OTHER_ROLE
import modules.ingestion.transformers.linkedin_2023_2024 as t1
import modules.ingestion.transformers.linkedin_1m_2024 as t2
import modules.ingestion.transformers.data_science_2024 as t3
import modules.ingestion.transformers.online_historical as t4
import modules.ingestion.transformers.philippines_kaggle as t5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

VALID_SENIORITY = {"entry_level", "mid", "senior", "unknown"}
VALID_COUNTRIES = {"PH", "US", "global"}


def _build_posting_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Generate deterministic posting_id for every row.

    Args:
        df: DataFrame with title, posted_date, source_dataset columns.

    Returns:
        DataFrame with posting_id column populated.
    """
    df = df.copy()
    df["posting_id"] = df.apply(
        lambda row: make_posting_id(
            source_dataset=str(row["source_dataset"]),
            native_id=None,
            title=str(row["title"]),
            posted_date=str(row["posted_date"]),
        ),
        axis=1,
    )
    return df


def _apply_role_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """Populate role_normalized from title using keyword-based mapping.

    Args:
        df: DataFrame with title column.

    Returns:
        DataFrame with role_normalized column populated.
    """
    df = df.copy()
    df["role_normalized"] = df["title"].apply(map_role)
    return df


def _validate_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove rows that fail the canonical quality gates.

    Quality gates (matching loader.py _validate_row):
    - title must not be empty
    - posted_date must be YYYY-MM
    - seniority must be a valid value
    - country must be a valid value
    - role_normalized must not be empty or 'Other'

    Args:
        df: Input DataFrame.

    Returns:
        Tuple of (valid_df, quarantine_count).
    """
    def _is_valid_period(value: str) -> bool:
        if len(value) != 7 or value[4] != "-":
            return False
        year, month = value[:4], value[5:]
        return year.isdigit() and month.isdigit() and 1 <= int(month) <= 12

    has_title = df["title"].str.strip().ne("").astype(bool)
    valid_date = df["posted_date"].apply(_is_valid_period).astype(bool)
    valid_seniority = df["seniority"].isin(VALID_SENIORITY).astype(bool)
    valid_country = df["country"].isin(VALID_COUNTRIES).astype(bool)
    has_role = df["role_normalized"].str.strip().ne("").astype(bool)
    not_other = (df["role_normalized"] != OTHER_ROLE).astype(bool)
    mask = has_title & valid_date & valid_seniority & valid_country & has_role & not_other
    quarantined = (~mask).sum()
    return df[mask].reset_index(drop=True), int(quarantined)


def _print_summary(df: pd.DataFrame, per_source: dict[str, int]) -> None:
    """Log a summary of the unified dataset.

    Args:
        df: Final unified DataFrame.
        per_source: Row counts per source before filtering.
    """
    logger.info("=" * 60)
    logger.info("BOOTSTRAP SUMMARY")
    logger.info("=" * 60)
    for source, count in per_source.items():
        logger.info("  %-45s %d rows (raw)", source, count)
    logger.info("  Final unified rows: %d", len(df))
    logger.info("  Date range: %s → %s", df["posted_date"].min(), df["posted_date"].max())
    logger.info("  Country distribution:")
    for country, count in df["country"].value_counts().items():
        logger.info("    %s: %d", country, count)
    logger.info("  role_normalized distribution (top 20):")
    for role, count in df["role_normalized"].value_counts().head(20).items():
        logger.info("    %-35s %d", role, count)
    logger.info("  Source distribution:")
    for src, count in df["source_dataset"].value_counts().items():
        logger.info("    %-45s %d", src, count)
    logger.info("=" * 60)


def run(output_path: Path, dry_run: bool = False) -> pd.DataFrame:
    """Execute the full bootstrap pipeline.

    Calls each transformer, concatenates, filters, maps roles, deduplicates,
    validates, and optionally writes the unified CSV.

    Args:
        output_path: Destination path for unified_job_postings.csv.
        dry_run: If True, print stats and return without writing the file.

    Returns:
        The final unified DataFrame.
    """
    raw_data_root = Path(settings.raw_data_path) / "kaggle"
    per_source_counts: dict[str, int] = {}
    frames: list[pd.DataFrame] = []

    sources = [
        ("linkedin_2023_2024", t1.transform, raw_data_root / "linkedin_2023_2024"),
        ("linkedin_1m_2024", t2.transform, raw_data_root / "linkedin_1m_2024"),
        ("data_science_2024", t3.transform, raw_data_root / "data_science_2024"),
        ("online_historical", t4.transform, raw_data_root / "online_historical"),
        ("philippines_kaggle", t5.transform, raw_data_root / "philippines"),
    ]

    for source_name, transform_fn, source_dir in sources:
        if not source_dir.exists() or not any(source_dir.iterdir()):
            logger.warning(
                "Source directory empty or missing: %s — skipping %s",
                source_dir,
                source_name,
            )
            continue
        try:
            df = transform_fn(source_dir)
            per_source_counts[source_name] = len(df)
            frames.append(df)
            logger.info("Loaded %s: %d rows", source_name, len(df))
        except (FileNotFoundError, ValueError) as exc:
            logger.error("Transformer failed for %s: %s — skipping", source_name, exc)

    if not frames:
        logger.error("No source data loaded. Bootstrap cannot continue.")
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    combined = pd.concat(frames, ignore_index=True)
    logger.info("Combined rows before tech filter: %d", len(combined))

    combined = filter_tech_jobs(combined, title_col="title")
    logger.info("Rows after tech filter: %d", len(combined))

    combined = _apply_role_mapping(combined)
    combined = _build_posting_ids(combined)

    combined = combined.drop_duplicates(subset=["posting_id"], keep="first")
    logger.info("Rows after dedup on posting_id: %d", len(combined))

    combined, quarantine_count = _validate_rows(combined)
    logger.info("Rows after quality gates: %d (quarantined: %d)", len(combined), quarantine_count)

    combined = combined.sort_values("posted_date").reset_index(drop=True)

    _print_summary(combined, per_source_counts)

    if dry_run:
        logger.info("Dry run — output not written.")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(output_path, index=False)
        logger.info("Unified dataset written to: %s", output_path)

    return combined


def main() -> None:
    """CLI entry point for the bootstrap script."""
    parser = argparse.ArgumentParser(
        description="Build unified_job_postings.csv from raw Kaggle sources."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(settings.processed_data_path) / "unified_job_postings.csv",
        help="Output CSV path (default: data/processed/unified_job_postings.csv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print statistics without writing the output file.",
    )
    args = parser.parse_args()

    result = run(output_path=args.output, dry_run=args.dry_run)

    if result.empty:
        logger.error("Bootstrap produced an empty dataset. Check source directories.")
        sys.exit(1)

    logger.info("Bootstrap complete. %d postings ready.", len(result))


if __name__ == "__main__":
    main()
