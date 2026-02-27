"""Orchestrator: the full load pipeline.

1. Read accession numbers
2. C-FIND each to get StudyInstanceUID + metadata
3. Start temporary SCP
4. C-MOVE each study to SCP (anonymize on receive)
5. Stop SCP
6. Update key.csv
7. Return summary
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from .audit import log_results
from .config import Config
from .keyfile import KeyEntry, next_case_id, read_key_file, write_key_file
from .pacs import find_by_accession, move_study
from .scp import TemporarySCP
from .verify import verify_load

log = logging.getLogger(__name__)


@dataclass
class LoadResult:
    case_id: str
    accession: str
    study_uid: str
    series_count: int
    image_count: int
    study_date: str
    modality: str
    description: str
    status: str  # "ok", "error", "skipped", or "dry-run"
    error: str | None = None
    duration_s: float | None = None


def load_studies(
    config: Config,
    project: str,
    accessions: list[str],
    dry_run: bool = False,
) -> tuple[list[LoadResult], dict]:
    """Load studies from PACS, anonymize, and save.

    Args:
        config: Application configuration.
        project: Project name (subdirectory under base_dir).
        accessions: List of accession numbers to load.
        dry_run: If True, only query PACS, don't retrieve images.

    Returns:
        Tuple of (results list, verification dict).
    """
    project_dir = config.output.base_dir / project
    key_path = project_dir / "key.csv"
    existing = read_key_file(key_path)

    # Check for already-loaded accessions
    loaded_accessions = {e.accession for e in existing}

    results: list[LoadResult] = []

    for ac in accessions:
        if ac in loaded_accessions:
            log.info("Skipping %s — already loaded", ac)
            results.append(
                LoadResult(
                    case_id="",
                    accession=ac,
                    study_uid="",
                    series_count=0,
                    image_count=0,
                    study_date="",
                    modality="",
                    description="",
                    status="skipped",
                    error="already loaded",
                )
            )
            continue

        # C-FIND
        try:
            studies = find_by_accession(config, ac)
        except Exception as e:
            log.error("C-FIND failed for %s: %s", ac, e)
            results.append(
                LoadResult(
                    case_id="",
                    accession=ac,
                    study_uid="",
                    series_count=0,
                    image_count=0,
                    study_date="",
                    modality="",
                    description="",
                    status="error",
                    error=f"C-FIND failed: {e}",
                )
            )
            continue

        if not studies:
            results.append(
                LoadResult(
                    case_id="",
                    accession=ac,
                    study_uid="",
                    series_count=0,
                    image_count=0,
                    study_date="",
                    modality="",
                    description="",
                    status="error",
                    error="not found on PACS",
                )
            )
            continue

        study = studies[0]
        study_uid = study.get("StudyInstanceUID", "")

        if dry_run:
            results.append(
                LoadResult(
                    case_id="(dry-run)",
                    accession=ac,
                    study_uid=study_uid,
                    series_count=int(study.get("NumberOfStudyRelatedSeries", 0) or 0),
                    image_count=int(study.get("NumberOfStudyRelatedInstances", 0) or 0),
                    study_date=study.get("StudyDate", ""),
                    modality=study.get("Modality", "") or study.get("ModalitiesInStudy", ""),
                    description=study.get("StudyDescription", ""),
                    status="dry-run",
                )
            )
            continue

        # Assign case ID
        case_id = next_case_id(existing)

        # C-MOVE with temporary SCP
        scp = TemporarySCP(config, project_dir, case_id)
        t0 = time.monotonic()
        try:
            scp.start()
            move_result = move_study(config, study_uid)
            # Wait briefly for any trailing C-STORE packets
            time.sleep(1)
        except Exception as e:
            elapsed = round(time.monotonic() - t0, 1)
            log.error("C-MOVE failed for %s: %s", ac, e)
            results.append(
                LoadResult(
                    case_id=case_id,
                    accession=ac,
                    study_uid=study_uid,
                    series_count=0,
                    image_count=0,
                    study_date=study.get("StudyDate", ""),
                    modality=study.get("Modality", "") or study.get("ModalitiesInStudy", ""),
                    description=study.get("StudyDescription", ""),
                    status="error",
                    error=f"C-MOVE failed: {e}",
                    duration_s=elapsed,
                )
            )
            continue
        finally:
            scp.stop()

        elapsed = round(time.monotonic() - t0, 1)

        series_count = len(scp.received_files)
        image_count = sum(len(files) for files in scp.received_files.values())

        entry = KeyEntry(
            case_id=case_id,
            accession=ac,
            study_date=study.get("StudyDate", ""),
            modality=study.get("Modality", "") or study.get("ModalitiesInStudy", ""),
            description=study.get("StudyDescription", ""),
            series_count=series_count,
            image_count=image_count,
        )
        existing.append(entry)
        write_key_file(key_path, existing)

        result = LoadResult(
            case_id=case_id,
            accession=ac,
            study_uid=study_uid,
            series_count=series_count,
            image_count=image_count,
            study_date=study.get("StudyDate", ""),
            modality=study.get("Modality", "") or study.get("ModalitiesInStudy", ""),
            description=study.get("StudyDescription", ""),
            status="ok",
            duration_s=elapsed,
        )
        results.append(result)
        log.info(
            "Loaded %s → %s (%d series, %d images)",
            ac, case_id, series_count, image_count,
        )

    # Verify results
    verification = verify_load(results)

    # Write load summary (includes verification)
    _write_load_json(project_dir / "load.json", results, verification)

    # Audit log
    log_results(config.output.base_dir, project, results, dry_run=dry_run)

    return results, verification


def result_to_dict(r: LoadResult) -> dict:
    """Convert a LoadResult to a JSON-serializable dict."""
    d = {
        "case_id": r.case_id,
        "accession": r.accession,
        "study_uid": r.study_uid,
        "series_count": r.series_count,
        "image_count": r.image_count,
        "study_date": r.study_date,
        "modality": r.modality,
        "description": r.description,
        "status": r.status,
    }
    if r.error:
        d["error"] = r.error
    if r.duration_s is not None:
        d["duration_s"] = r.duration_s
    return d


def _write_load_json(
    path: Path, results: list[LoadResult], verification: dict,
) -> None:
    """Write machine-readable load summary."""
    data = {
        "results": [result_to_dict(r) for r in results],
        "verification": verification,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
