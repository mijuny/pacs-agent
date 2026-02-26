"""Test key CSV file handling."""

from pathlib import Path

from agent_rad_tools.keyfile import KeyEntry, next_case_id, read_key_file, write_key_file


class TestKeyFileRoundtrip:
    def test_write_and_read(self, tmp_path: Path):
        path = tmp_path / "key.csv"
        entries = [
            KeyEntry("case0001", "AC001", "20240101", "CT", "Head CT", 3, 150),
            KeyEntry("case0002", "AC002", "20240102", "MR", "Brain MRI", 5, 300),
        ]

        write_key_file(path, entries)
        loaded = read_key_file(path)

        assert len(loaded) == 2
        assert loaded[0].case_id == "case0001"
        assert loaded[0].accession == "AC001"
        assert loaded[0].series_count == 3
        assert loaded[0].image_count == 150
        assert loaded[1].case_id == "case0002"
        assert loaded[1].modality == "MR"

    def test_read_nonexistent(self, tmp_path: Path):
        result = read_key_file(tmp_path / "missing.csv")
        assert result == []

    def test_creates_parent_dirs(self, tmp_path: Path):
        path = tmp_path / "a" / "b" / "key.csv"
        write_key_file(path, [KeyEntry("case0001", "AC001", "", "", "", 0, 0)])
        assert path.exists()

    def test_empty_file(self, tmp_path: Path):
        path = tmp_path / "key.csv"
        write_key_file(path, [])
        loaded = read_key_file(path)
        assert loaded == []


class TestNextCaseId:
    def test_empty_list(self):
        assert next_case_id([]) == "case0001"

    def test_increments(self):
        entries = [
            KeyEntry("case0001", "AC001", "", "", "", 0, 0),
            KeyEntry("case0002", "AC002", "", "", "", 0, 0),
        ]
        assert next_case_id(entries) == "case0003"

    def test_finds_max(self):
        entries = [
            KeyEntry("case0001", "AC001", "", "", "", 0, 0),
            KeyEntry("case0010", "AC010", "", "", "", 0, 0),
            KeyEntry("case0003", "AC003", "", "", "", 0, 0),
        ]
        assert next_case_id(entries) == "case0011"

    def test_handles_non_standard_ids(self):
        entries = [
            KeyEntry("custom_id", "AC001", "", "", "", 0, 0),
            KeyEntry("case0005", "AC002", "", "", "", 0, 0),
        ]
        assert next_case_id(entries) == "case0006"
