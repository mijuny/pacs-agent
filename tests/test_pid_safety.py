"""Byte-level PID safety scan of anonymized DICOM files.

Verifies that known PHI strings from the original files
do NOT appear anywhere in the anonymized output — not in
tags, not in binary data, not in any form.

Note: Short PHI strings (< 5 chars) are excluded from byte-level
scanning because they cause false positives in binary pixel data.
Tag-level checks handle those cases instead.
"""

from __future__ import annotations

from pathlib import Path

import pydicom
from pydicom.tag import Tag

from pacs_agent.anonymize import anonymize_file
from pacs_agent.tags import PHI_TAGS

# Minimum PHI string length for byte-level scan.
# Shorter strings appear randomly in binary pixel data.
MIN_PHI_SCAN_LEN = 5

# Known PHI values from the test DICOM files (>= MIN_PHI_SCAN_LEN)
KNOWN_PHI = [
    b"CompressedSamples",   # PatientName component from CT1
    b"JFK IMAGING CENTER",  # InstitutionName from CT1
    b"CompressedSamples^CT1",
]


class TestBytelevelPIDSafety:
    def test_no_phi_in_anonymized_bytes(self, ct1_path: Path, tmp_path: Path):
        """Scan entire anonymized file bytes for known PHI strings."""
        dst = tmp_path / "pid_check.dcm"
        anonymize_file(ct1_path, dst, "case0001")

        raw_bytes = dst.read_bytes()
        for phi in KNOWN_PHI:
            assert phi not in raw_bytes, (
                f"PHI string {phi!r} found in anonymized file"
            )

    def test_case_id_present(self, ct1_path: Path, tmp_path: Path):
        """Verify the case ID IS present (sanity check)."""
        dst = tmp_path / "pid_check2.dcm"
        anonymize_file(ct1_path, dst, "case0001")

        raw_bytes = dst.read_bytes()
        assert b"case0001" in raw_bytes

    def test_deident_marker_present(self, ct1_path: Path, tmp_path: Path):
        """Verify deidentification marker is in the file."""
        dst = tmp_path / "pid_check3.dcm"
        anonymize_file(ct1_path, dst, "case0001")

        raw_bytes = dst.read_bytes()
        assert b"pacs-agent allowlist v1" in raw_bytes


class TestTagLevelPIDSafety:
    """Verify no PHI tags remain at the DICOM tag level."""

    def test_no_phi_tags_in_output(self, ct1_path: Path, tmp_path: Path):
        dst = tmp_path / "tag_check.dcm"
        anonymize_file(ct1_path, dst, "case0001")

        ds = pydicom.dcmread(dst)
        # PatientName and PatientID are re-set to case_id
        reset_tags = {Tag(0x0010, 0x0010), Tag(0x0010, 0x0020)}
        for tag in PHI_TAGS:
            if tag in reset_tags:
                continue
            assert tag not in ds, f"PHI tag {tag} in anonymized file"

    def test_patient_fields_are_case_id(self, ct1_path: Path, tmp_path: Path):
        dst = tmp_path / "tag_check2.dcm"
        anonymize_file(ct1_path, dst, "case0001")

        ds = pydicom.dcmread(dst)
        assert str(ds.PatientName) == "case0001"
        assert ds.PatientID == "case0001"


class TestAllTestFilesSafety:
    def test_all_test_files_no_phi_tags(self, tmp_dcm_dir: Path, tmp_path: Path):
        """Anonymize all test files and verify no PHI tags remain.

        Tag-level check is more reliable than byte-level scanning across
        diverse test files, since manufacturer names and other safe values
        can collide with PHI values (e.g. "TOSHIBA" as InstitutionName
        AND Manufacturer).
        """
        from pacs_agent.tags import is_private_tag

        reset_tags = {Tag(0x0010, 0x0010), Tag(0x0010, 0x0020)}

        for dcm_file in sorted(tmp_dcm_dir.glob("*.dcm")):
            dst = tmp_path / f"anon_{dcm_file.name}"
            anonymize_file(dcm_file, dst, "case9999")

            ds = pydicom.dcmread(dst)

            # No PHI tags (except re-set ones)
            for tag in PHI_TAGS:
                if tag in reset_tags:
                    continue
                assert tag not in ds, (
                    f"PHI tag {tag} in {dcm_file.name}"
                )

            # No private tags
            for elem in ds:
                assert not is_private_tag(elem.tag), (
                    f"Private tag {elem.tag} in {dcm_file.name}"
                )

            # Patient fields set to case ID
            assert str(ds.PatientName) == "case9999"
            assert ds.PatientID == "case9999"
            assert ds.PatientIdentityRemoved == "YES"
