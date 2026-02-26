"""Test load verification and project-wide outlier detection."""

from dataclasses import dataclass

from agent_rad_tools.keyfile import KeyEntry
from agent_rad_tools.verify import verify_load, verify_project


@dataclass
class FakeResult:
    accession: str
    case_id: str
    status: str
    image_count: int = 100
    series_count: int = 5
    modality: str = "MR"
    error: str | None = None
    duration_s: float | None = None


class TestVerifyLoad:
    def test_all_ok(self):
        results = [
            FakeResult("AC001", "case0001", "ok", image_count=200),
            FakeResult("AC002", "case0002", "ok", image_count=300),
        ]
        v = verify_load(results)
        assert v["ok"] is True
        assert v["loaded"] == 2
        assert v["failed"] == 0
        assert v["not_found"] == 0
        assert v["skipped"] == 0
        assert v["warnings"] == []

    def test_not_found(self):
        results = [
            FakeResult("AC001", "case0001", "ok", image_count=200),
            FakeResult("AC002", "", "error", error="not found on PACS"),
        ]
        v = verify_load(results)
        assert v["ok"] is False
        assert v["loaded"] == 1
        assert v["not_found"] == 1

    def test_failed(self):
        results = [
            FakeResult("AC001", "case0001", "error", error="C-MOVE failed: timeout"),
        ]
        v = verify_load(results)
        assert v["ok"] is False
        assert v["failed"] == 1
        assert v["not_found"] == 0

    def test_low_image_count_warning(self):
        results = [
            FakeResult("AC001", "case0001", "ok", image_count=2),
        ]
        v = verify_load(results)
        assert v["ok"] is False
        assert len(v["warnings"]) == 1
        assert "unusually low" in v["warnings"][0]

    def test_high_image_count_warning(self):
        results = [
            FakeResult("AC001", "case0001", "ok", image_count=6200),
        ]
        v = verify_load(results)
        assert v["ok"] is False
        assert len(v["warnings"]) == 1
        assert "unusually high" in v["warnings"][0]

    def test_skipped_not_counted_as_failure(self):
        results = [
            FakeResult("AC001", "", "skipped", error="already loaded"),
            FakeResult("AC002", "case0001", "ok", image_count=200),
        ]
        v = verify_load(results)
        assert v["ok"] is True
        assert v["skipped"] == 1
        assert v["loaded"] == 1

    def test_dry_run_not_counted(self):
        results = [
            FakeResult("AC001", "(dry-run)", "dry-run", image_count=200),
        ]
        v = verify_load(results)
        assert v["ok"] is True
        assert v["loaded"] == 0
        assert v["total_requested"] == 1


class TestVerifyProject:
    def test_too_few_cases(self):
        entries = [
            KeyEntry("case0001", "AC001", "20240101", "MR", "Brain", 5, 300),
            KeyEntry("case0002", "AC002", "20240102", "MR", "Brain", 5, 300),
        ]
        v = verify_project(entries)
        assert v["ok"] is True
        assert "note" in v

    def test_all_similar(self):
        entries = [
            KeyEntry("case0001", "AC001", "20240101", "MR", "Brain", 5, 300),
            KeyEntry("case0002", "AC002", "20240102", "MR", "Brain", 6, 350),
            KeyEntry("case0003", "AC003", "20240103", "MR", "Brain", 5, 280),
        ]
        v = verify_project(entries)
        assert v["ok"] is True
        assert v["warnings"] == []

    def test_series_count_outlier(self):
        entries = [
            KeyEntry("case0001", "AC001", "20240101", "MR", "Brain", 10, 300),
            KeyEntry("case0002", "AC002", "20240102", "MR", "Brain", 10, 300),
            KeyEntry("case0003", "AC003", "20240103", "MR", "Brain", 2, 300),
        ]
        v = verify_project(entries)
        assert v["ok"] is False
        assert any("case0003" in w and "series" in w for w in v["warnings"])

    def test_image_count_outlier_low(self):
        entries = [
            KeyEntry("case0001", "AC001", "20240101", "MR", "Brain", 5, 450),
            KeyEntry("case0002", "AC002", "20240102", "MR", "Brain", 5, 500),
            KeyEntry("case0003", "AC003", "20240103", "MR", "Brain", 5, 45),
        ]
        v = verify_project(entries)
        assert v["ok"] is False
        assert any("case0003" in w and "images" in w for w in v["warnings"])

    def test_image_count_outlier_high(self):
        entries = [
            KeyEntry("case0001", "AC001", "20240101", "MR", "Brain", 5, 450),
            KeyEntry("case0002", "AC002", "20240102", "MR", "Brain", 5, 500),
            KeyEntry("case0003", "AC003", "20240103", "MR", "Brain", 5, 5000),
        ]
        v = verify_project(entries)
        assert v["ok"] is False
        assert any("case0003" in w and "images" in w for w in v["warnings"])

    def test_modality_mismatch(self):
        entries = [
            KeyEntry("case0001", "AC001", "20240101", "MR", "Brain", 5, 300),
            KeyEntry("case0002", "AC002", "20240102", "MR", "Brain", 5, 300),
            KeyEntry("case0003", "AC003", "20240103", "CR", "Chest", 5, 300),
        ]
        v = verify_project(entries)
        assert v["ok"] is False
        assert any("modality" in w and "CR" in w for w in v["warnings"])
