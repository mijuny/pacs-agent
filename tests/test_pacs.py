"""Mock-based tests for PACS operations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pydicom.dataset import Dataset

from pacs_agent.config import Config, OutputConfig, PacsConfig, ScpConfig
from pacs_agent.pacs import _extract_safe_fields


def _make_config() -> Config:
    return Config(
        pacs=PacsConfig(host="192.168.1.1", port=104, ae_title="TEST_PACS"),
        scp=ScpConfig(ae_title="TEST_SCP", port=9012),
        output=OutputConfig(),
    )


class TestExtractSafeFields:
    def test_extracts_safe_fields_only(self):
        ds = Dataset()
        ds.AccessionNumber = "AC12345"
        ds.StudyInstanceUID = "1.2.3.4.5"
        ds.Modality = "CT"
        ds.StudyDate = "20240101"
        ds.StudyDescription = "Head CT"
        ds.PatientName = "Smith^John"  # PHI — should NOT be extracted
        ds.PatientID = "12345"  # PHI — should NOT be extracted

        result = _extract_safe_fields(ds)

        assert result["AccessionNumber"] == "AC12345"
        assert result["Modality"] == "CT"
        assert result["StudyDate"] == "20240101"
        assert "PatientName" not in result
        assert "PatientID" not in result

    def test_missing_fields_skipped(self):
        ds = Dataset()
        ds.Modality = "MR"
        # No other fields set

        result = _extract_safe_fields(ds)

        assert result["Modality"] == "MR"
        assert "AccessionNumber" not in result


class TestEcho:
    @patch("pacs_agent.pacs.AE")
    def test_echo_success(self, mock_ae_cls):
        config = _make_config()

        mock_ae = MagicMock()
        mock_ae_cls.return_value = mock_ae
        mock_assoc = MagicMock()
        mock_assoc.is_established = True
        mock_status = MagicMock()
        mock_status.Status = 0x0000
        mock_assoc.send_c_echo.return_value = mock_status
        mock_ae.associate.return_value = mock_assoc

        from pacs_agent.pacs import echo
        result = echo(config)

        assert result is True
        mock_assoc.release.assert_called_once()

    @patch("pacs_agent.pacs.AE")
    def test_echo_not_established(self, mock_ae_cls):
        config = _make_config()

        mock_ae = MagicMock()
        mock_ae_cls.return_value = mock_ae
        mock_assoc = MagicMock()
        mock_assoc.is_established = False
        mock_ae.associate.return_value = mock_assoc

        from pacs_agent.pacs import echo
        result = echo(config)

        assert result is False


class TestFindByAccession:
    @patch("pacs_agent.pacs.AE")
    def test_returns_safe_fields(self, mock_ae_cls):
        config = _make_config()

        # Set up mock
        mock_ae = MagicMock()
        mock_ae_cls.return_value = mock_ae
        mock_assoc = MagicMock()
        mock_assoc.is_established = True
        mock_ae.associate.return_value = mock_assoc

        # Create a response dataset
        response_ds = Dataset()
        response_ds.AccessionNumber = "AC001"
        response_ds.StudyInstanceUID = "1.2.3.4.5"
        response_ds.Modality = "CT"
        response_ds.PatientName = "REAL_NAME"  # Should NOT appear in result

        mock_status = MagicMock()
        mock_status.Status = 0xFF00
        mock_assoc.send_c_find.return_value = [(mock_status, response_ds)]

        from pacs_agent.pacs import find_by_accession
        results = find_by_accession(config, "AC001")

        assert len(results) == 1
        assert results[0]["AccessionNumber"] == "AC001"
        assert "PatientName" not in results[0]
        mock_assoc.release.assert_called_once()
