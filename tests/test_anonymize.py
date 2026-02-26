"""Test DICOM file anonymization with real test files."""

from __future__ import annotations

from pathlib import Path

import pydicom
from pydicom.tag import Tag

from agent_rad_tools.anonymize import anonymize_dataset, anonymize_file
from agent_rad_tools.tags import PHI_TAGS, is_private_tag

# Tags we explicitly re-set with case_id — they'll be present but safe
_RESET_TAGS = {Tag(0x0010, 0x0010), Tag(0x0010, 0x0020)}


class TestAnonymizeDataset:
    def test_phi_tags_removed_or_replaced(self, ct1_path: Path):
        ds = pydicom.dcmread(ct1_path)
        original_name = str(ds.PatientName)
        original_id = ds.PatientID
        assert original_name != ""
        assert original_id != ""

        anonymize_dataset(ds, "case0001")

        for tag in PHI_TAGS:
            if tag in _RESET_TAGS:
                # These are re-set to case_id
                continue
            assert tag not in ds, f"PHI tag {tag} still present"

        # Verify re-set tags have case_id, not original values
        assert str(ds.PatientName) == "case0001"
        assert ds.PatientID == "case0001"
        assert str(ds.PatientName) != original_name
        assert ds.PatientID != original_id

    def test_patient_fields_set_to_case_id(self, ct1_path: Path):
        ds = pydicom.dcmread(ct1_path)
        anonymize_dataset(ds, "case0042")
        assert str(ds.PatientName) == "case0042"
        assert ds.PatientID == "case0042"

    def test_deidentification_marked(self, ct1_path: Path):
        ds = pydicom.dcmread(ct1_path)
        anonymize_dataset(ds, "case0001")
        assert ds.PatientIdentityRemoved == "YES"
        assert "allowlist" in ds.DeidentificationMethod

    def test_private_tags_removed(self, ct1_path: Path):
        ds = pydicom.dcmread(ct1_path)
        private_before = [e.tag for e in ds if is_private_tag(e.tag)]
        assert len(private_before) > 0, "Test file should have private tags"

        anonymize_dataset(ds, "case0001")

        private_after = [e.tag for e in ds if is_private_tag(e.tag)]
        assert len(private_after) == 0, f"Private tags remain: {private_after}"

    def test_safe_tags_preserved(self, ct1_path: Path):
        ds = pydicom.dcmread(ct1_path)
        original_modality = ds.Modality
        original_rows = ds.Rows
        original_cols = ds.Columns

        anonymize_dataset(ds, "case0001")

        assert ds.Modality == original_modality
        assert ds.Rows == original_rows
        assert ds.Columns == original_cols

    def test_pixel_data_preserved(self, ct1_path: Path):
        """Verify pixel data tag survives anonymization."""
        ds = pydicom.dcmread(ct1_path)
        assert Tag(0x7FE0, 0x0010) in ds

        anonymize_dataset(ds, "case0001")

        assert Tag(0x7FE0, 0x0010) in ds
        # Verify pixel data length is unchanged
        assert len(ds.PixelData) > 0

    def test_study_uid_preserved(self, ct1_path: Path):
        ds = pydicom.dcmread(ct1_path)
        original_uid = ds.StudyInstanceUID

        anonymize_dataset(ds, "case0001")

        assert ds.StudyInstanceUID == original_uid

    def test_accession_preserved(self, ct1_path: Path):
        ds = pydicom.dcmread(ct1_path)
        ds.AccessionNumber = "TEST12345"

        anonymize_dataset(ds, "case0001")

        assert ds.AccessionNumber == "TEST12345"

    def test_study_id_removed(self, ct1_path: Path):
        """StudyID can mirror PatientID — should not survive."""
        ds = pydicom.dcmread(ct1_path)
        ds.StudyID = "SENSITIVE123"

        anonymize_dataset(ds, "case0001")

        assert Tag(0x0020, 0x0010) not in ds


class TestAnonymizeFile:
    def test_roundtrip(self, ct1_path: Path, tmp_path: Path):
        dst = tmp_path / "anon.dcm"
        anonymize_file(ct1_path, dst, "case0001")

        assert dst.exists()
        ds = pydicom.dcmread(dst)
        assert str(ds.PatientName) == "case0001"
        assert ds.PatientID == "case0001"
        assert ds.PatientIdentityRemoved == "YES"

    def test_creates_parent_dirs(self, ct1_path: Path, tmp_path: Path):
        dst = tmp_path / "a" / "b" / "c" / "anon.dcm"
        anonymize_file(ct1_path, dst, "case0001")
        assert dst.exists()

    def test_mr_file(self, mr1_path: Path, tmp_path: Path):
        dst = tmp_path / "anon_mr.dcm"
        anonymize_file(mr1_path, dst, "case0002")

        ds = pydicom.dcmread(dst)
        assert str(ds.PatientName) == "case0002"
        assert ds.Modality == "MR"
        # No original PHI tags (except re-set ones)
        for tag in PHI_TAGS:
            if tag in _RESET_TAGS:
                continue
            assert tag not in ds, f"PHI tag {tag} in anonymized MR"
