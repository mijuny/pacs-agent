"""Verify PHI tag coverage and allowlist correctness."""

from pydicom.tag import Tag

from pacs_agent.tags import KEEP_TAGS, PHI_TAGS, is_private_tag


class TestPHICoverage:
    """Ensure all critical PHI tags are in the removal set."""

    def test_patient_name(self):
        assert Tag(0x0010, 0x0010) in PHI_TAGS

    def test_patient_id(self):
        assert Tag(0x0010, 0x0020) in PHI_TAGS

    def test_patient_birth_date(self):
        assert Tag(0x0010, 0x0030) in PHI_TAGS

    def test_other_patient_ids(self):
        assert Tag(0x0010, 0x1000) in PHI_TAGS

    def test_other_patient_names(self):
        assert Tag(0x0010, 0x1001) in PHI_TAGS

    def test_issuer_of_patient_id(self):
        assert Tag(0x0010, 0x0021) in PHI_TAGS

    def test_patient_address(self):
        assert Tag(0x0010, 0x1040) in PHI_TAGS

    def test_patient_telephone(self):
        assert Tag(0x0010, 0x2154) in PHI_TAGS

    def test_referring_physician(self):
        assert Tag(0x0008, 0x0090) in PHI_TAGS

    def test_performing_physician(self):
        assert Tag(0x0008, 0x1050) in PHI_TAGS

    def test_operators_name(self):
        assert Tag(0x0008, 0x1070) in PHI_TAGS

    def test_requesting_physician(self):
        assert Tag(0x0032, 0x1032) in PHI_TAGS

    def test_institution_name(self):
        assert Tag(0x0008, 0x0080) in PHI_TAGS

    def test_institution_address(self):
        assert Tag(0x0008, 0x0081) in PHI_TAGS

    def test_additional_patient_history(self):
        assert Tag(0x0010, 0x21B0) in PHI_TAGS

    def test_patient_comments(self):
        assert Tag(0x0010, 0x4000) in PHI_TAGS

    def test_request_attributes_sequence(self):
        assert Tag(0x0040, 0x0275) in PHI_TAGS


class TestAllowlistCorrectness:
    """Verify the KEEP list has the right tags and no PHI."""

    def test_no_phi_in_keep(self):
        overlap = PHI_TAGS & KEEP_TAGS
        assert not overlap, f"PHI tags in KEEP list: {overlap}"

    def test_accession_number_kept(self):
        assert Tag(0x0008, 0x0050) in KEEP_TAGS

    def test_study_uid_kept(self):
        assert Tag(0x0020, 0x000D) in KEEP_TAGS

    def test_series_uid_kept(self):
        assert Tag(0x0020, 0x000E) in KEEP_TAGS

    def test_modality_kept(self):
        assert Tag(0x0008, 0x0060) in KEEP_TAGS

    def test_pixel_data_kept(self):
        assert Tag(0x7FE0, 0x0010) in KEEP_TAGS

    def test_rows_cols_kept(self):
        assert Tag(0x0028, 0x0010) in KEEP_TAGS  # Rows
        assert Tag(0x0028, 0x0011) in KEEP_TAGS  # Columns

    def test_transfer_syntax_kept(self):
        assert Tag(0x0002, 0x0010) in KEEP_TAGS


class TestPrivateTagDetection:
    def test_odd_group_is_private(self):
        assert is_private_tag(Tag(0x0009, 0x0010))
        assert is_private_tag(Tag(0x0011, 0x1010))

    def test_even_group_is_not_private(self):
        assert not is_private_tag(Tag(0x0010, 0x0010))
        assert not is_private_tag(Tag(0x0008, 0x0060))
