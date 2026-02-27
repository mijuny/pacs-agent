"""Key CSV file handling.

The key file maps case IDs to accession numbers and study metadata.
Written after each successful load, read to determine next case ID.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class KeyEntry:
    case_id: str
    accession: str
    study_date: str
    modality: str
    description: str
    series_count: int
    image_count: int


FIELDNAMES = [
    "case_id",
    "accession",
    "study_date",
    "modality",
    "description",
    "series_count",
    "image_count",
]


def read_key_file(path: Path) -> list[KeyEntry]:
    """Read existing key.csv, return empty list if it doesn't exist."""
    if not path.exists():
        return []

    entries = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append(
                KeyEntry(
                    case_id=row["case_id"],
                    accession=row["accession"],
                    study_date=row.get("study_date", ""),
                    modality=row.get("modality", ""),
                    description=row.get("description", ""),
                    series_count=int(row.get("series_count", 0)),
                    image_count=int(row.get("image_count", 0)),
                )
            )
    return entries


def write_key_file(path: Path, entries: list[KeyEntry]) -> None:
    """Write key.csv with all entries."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for e in entries:
            writer.writerow(
                {
                    "case_id": e.case_id,
                    "accession": e.accession,
                    "study_date": e.study_date,
                    "modality": e.modality,
                    "description": e.description,
                    "series_count": e.series_count,
                    "image_count": e.image_count,
                }
            )


def next_case_id(entries: list[KeyEntry]) -> str:
    """Generate next case ID based on existing entries.

    Returns "case0001" if no entries, increments from highest existing.
    """
    if not entries:
        return "case0001"

    max_num = 0
    for e in entries:
        if e.case_id.startswith("case"):
            try:
                num = int(e.case_id[4:])
                max_num = max(max_num, num)
            except ValueError:
                pass
    return f"case{max_num + 1:04d}"
