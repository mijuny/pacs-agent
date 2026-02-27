"""Verification of load results and project-wide outlier detection."""

from __future__ import annotations

from collections import Counter
from statistics import median


def verify_load(results: list) -> dict:
    """Verify load results: count outcomes and flag unusual image counts.

    Args:
        results: List of LoadResult objects from load_studies().

    Returns:
        Dict with ok, counts, and warnings list.
    """
    loaded = 0
    skipped = 0
    failed = 0
    not_found = 0
    warnings: list[str] = []

    for r in results:
        if r.status == "ok":
            loaded += 1
            if r.image_count < 5:
                warnings.append(
                    f"{r.accession} ({r.case_id}): only {r.image_count} images"
                    " (unusually low)"
                )
            elif r.image_count > 5000:
                warnings.append(
                    f"{r.accession} ({r.case_id}): {r.image_count} images"
                    " (unusually high)"
                )
        elif r.status == "skipped":
            skipped += 1
        elif r.status == "dry-run":
            pass  # not counted as failure
        elif r.status == "error":
            if r.error and "not found" in r.error:
                not_found += 1
            else:
                failed += 1

    return {
        "ok": failed == 0 and not_found == 0 and len(warnings) == 0,
        "total_requested": len(results),
        "loaded": loaded,
        "skipped": skipped,
        "failed": failed,
        "not_found": not_found,
        "warnings": warnings,
    }


def verify_project(entries: list) -> dict:
    """Compare cases within a project to find outliers.

    Args:
        entries: List of KeyEntry objects from key.csv.

    Returns:
        Dict with ok, median stats, and warnings list.
    """
    if len(entries) < 3:
        return {"ok": True, "warnings": [], "note": "too few cases to compare"}

    series_counts = [e.series_count for e in entries]
    image_counts = [e.image_count for e in entries]
    med_series = median(series_counts)
    med_images = median(image_counts)

    modalities = Counter(e.modality for e in entries)
    majority_modality = modalities.most_common(1)[0][0]

    warnings: list[str] = []
    for e in entries:
        if med_series > 0 and e.series_count < med_series / 2:
            warnings.append(
                f"{e.case_id}: {e.series_count} series vs median {med_series:.0f}"
                " — possibly incomplete study"
            )
        if med_series > 0 and e.series_count > med_series * 2:
            warnings.append(
                f"{e.case_id}: {e.series_count} series vs median {med_series:.0f}"
                " — unusually many series"
            )
        if med_images > 0 and e.image_count < med_images / 3:
            warnings.append(
                f"{e.case_id}: {e.image_count} images vs median {med_images:.0f}"
                " — much fewer than others"
            )
        if med_images > 0 and e.image_count > med_images * 3:
            warnings.append(
                f"{e.case_id}: {e.image_count} images vs median {med_images:.0f}"
                " — much more than others"
            )
        if e.modality != majority_modality:
            warnings.append(
                f"{e.case_id}: modality {e.modality} differs from"
                f" majority {majority_modality}"
            )

    return {
        "ok": len(warnings) == 0,
        "median_series": med_series,
        "median_images": med_images,
        "warnings": warnings,
    }
