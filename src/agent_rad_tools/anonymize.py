"""File-level DICOM anonymization using allowlist approach.

Only tags in KEEP_TAGS survive. PHI tags are explicitly deleted,
private tags are removed, and unknown tags are deleted. Patient
identity fields are replaced with the case ID.
"""

from __future__ import annotations

from pathlib import Path

from pydicom import dcmread
from pydicom.dataset import Dataset

from .tags import KEEP_TAGS, PHI_TAGS, is_private_tag


def anonymize_dataset(ds: Dataset, case_id: str) -> Dataset:
    """Anonymize a DICOM dataset in place.

    Args:
        ds: pydicom Dataset (modified in place).
        case_id: Case identifier (e.g. "case0001") to replace patient fields.

    Returns:
        The modified dataset.
    """
    # Collect tags to delete (iterate over copy of keys)
    tags_to_delete = []
    for elem in ds:
        tag = elem.tag
        # Keep file meta info group — handled separately
        if tag.group == 0x0002:
            continue
        # Delete private tags
        if is_private_tag(tag):
            tags_to_delete.append(tag)
        # Delete PHI tags
        elif tag in PHI_TAGS:
            tags_to_delete.append(tag)
        # Delete sequences not on allowlist
        elif elem.VR == "SQ" and tag not in KEEP_TAGS:
            tags_to_delete.append(tag)
        # Delete unknown tags not on allowlist
        elif tag not in KEEP_TAGS:
            tags_to_delete.append(tag)

    for tag in tags_to_delete:
        del ds[tag]

    # Set patient identity fields to case ID
    ds.PatientName = case_id
    ds.PatientID = case_id

    # Mark as deidentified
    ds.PatientIdentityRemoved = "YES"
    ds.DeidentificationMethod = "agent-rad-tools allowlist v1"

    return ds


def anonymize_file(
    src: Path,
    dst: Path,
    case_id: str,
) -> None:
    """Read a DICOM file, anonymize it, and save to dst.

    Args:
        src: Source DICOM file path.
        dst: Destination path for anonymized file.
        case_id: Case identifier for patient fields.
    """
    ds = dcmread(src)
    anonymize_dataset(ds, case_id)
    dst.parent.mkdir(parents=True, exist_ok=True)
    ds.save_as(dst)
