"""PACS operations: C-ECHO, C-FIND, C-MOVE.

All operations are synchronous (pynetdicom is sync).
PHI may be returned by PACS but is never exposed in return values —
only safe metadata fields are included in results.
"""

from __future__ import annotations

import logging

from pydicom.dataset import Dataset
from pynetdicom import AE
from pynetdicom.sop_class import (
    StudyRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelMove,
    Verification,
)

from .config import Config

log = logging.getLogger(__name__)


def echo(config: Config) -> bool:
    """Test PACS connectivity with C-ECHO.

    Returns True if association + echo succeeded.
    """
    ae = AE(ae_title=config.scp.ae_title)
    ae.add_requested_context(Verification)

    assoc = ae.associate(
        config.pacs.host,
        config.pacs.port,
        ae_title=config.pacs.ae_title,
    )
    if not assoc.is_established:
        return False

    try:
        status = assoc.send_c_echo()
        return status and status.Status == 0x0000
    finally:
        assoc.release()


def find_by_accession(
    config: Config,
    accession: str,
) -> list[dict[str, str]]:
    """C-FIND studies by AccessionNumber.

    Returns list of dicts with safe metadata only.
    PHI fields are never included in the return value.
    """
    ae = AE(ae_title=config.scp.ae_title)
    ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)

    ds = Dataset()
    ds.QueryRetrieveLevel = "STUDY"
    ds.AccessionNumber = accession

    # Request safe metadata fields
    ds.StudyInstanceUID = ""
    ds.Modality = ""
    ds.ModalitiesInStudy = ""
    ds.StudyDate = ""
    ds.StudyTime = ""
    ds.StudyDescription = ""
    ds.NumberOfStudyRelatedSeries = ""
    ds.NumberOfStudyRelatedInstances = ""
    ds.PatientSex = ""
    ds.PatientAge = ""

    assoc = ae.associate(
        config.pacs.host,
        config.pacs.port,
        ae_title=config.pacs.ae_title,
    )
    if not assoc.is_established:
        raise ConnectionError(
            f"Cannot associate with {config.pacs.ae_title} "
            f"at {config.pacs.host}:{config.pacs.port}"
        )

    results: list[dict[str, str]] = []
    try:
        responses = assoc.send_c_find(
            ds, StudyRootQueryRetrieveInformationModelFind
        )
        for status, identifier in responses:
            if status and status.Status in (0xFF00, 0xFF01) and identifier:
                results.append(_extract_safe_fields(identifier))
    finally:
        assoc.release()

    return results


def move_study(
    config: Config,
    study_uid: str,
) -> dict[str, int]:
    """C-MOVE a study to our SCP.

    Args:
        config: PACS and SCP configuration.
        study_uid: StudyInstanceUID to retrieve.

    Returns:
        Dict with completed/failed/warning counts.
    """
    ae = AE(ae_title=config.scp.ae_title)
    ae.add_requested_context(StudyRootQueryRetrieveInformationModelMove)

    ds = Dataset()
    ds.QueryRetrieveLevel = "STUDY"
    ds.StudyInstanceUID = study_uid

    assoc = ae.associate(
        config.pacs.host,
        config.pacs.port,
        ae_title=config.pacs.ae_title,
    )
    if not assoc.is_established:
        raise ConnectionError(
            f"Cannot associate with {config.pacs.ae_title} "
            f"at {config.pacs.host}:{config.pacs.port}"
        )

    result = {"completed": 0, "failed": 0, "warning": 0}
    try:
        responses = assoc.send_c_move(
            ds,
            config.scp.ae_title,
            StudyRootQueryRetrieveInformationModelMove,
        )
        for status, identifier in responses:
            if status:
                s = status.Status
                if s == 0x0000:  # success
                    result["completed"] = getattr(
                        status, "NumberOfCompletedSubOperations", 0
                    )
                    result["failed"] = getattr(
                        status, "NumberOfFailedSubOperations", 0
                    )
                    result["warning"] = getattr(
                        status, "NumberOfWarningSubOperations", 0
                    )
                elif s == 0xC000:
                    raise RuntimeError(
                        f"C-MOVE failed with status 0x{s:04X}"
                    )
    finally:
        assoc.release()

    return result


# ── Safe field extraction (no PHI leaks) ──────────────────────

_SAFE_KEYWORDS = [
    "AccessionNumber",
    "StudyInstanceUID",
    "Modality",
    "ModalitiesInStudy",
    "StudyDate",
    "StudyTime",
    "StudyDescription",
    "NumberOfStudyRelatedSeries",
    "NumberOfStudyRelatedInstances",
    "PatientSex",
    "PatientAge",
]


def _extract_safe_fields(ds: Dataset) -> dict[str, str]:
    """Extract only safe metadata fields from a C-FIND response."""
    result: dict[str, str] = {}
    for kw in _SAFE_KEYWORDS:
        val = getattr(ds, kw, None)
        if val is not None:
            result[kw] = str(val)
    return result
