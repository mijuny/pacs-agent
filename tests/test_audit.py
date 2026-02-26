"""Test audit logging."""

from dataclasses import dataclass
from pathlib import Path

from agent_rad_tools.audit import get_db, log_results, query_audit


@dataclass
class FakeResult:
    accession: str
    case_id: str
    status: str
    modality: str = "MR"
    image_count: int = 100
    series_count: int = 5
    duration_s: float | None = None
    error: str | None = None


class TestAuditDB:
    def test_creates_db(self, tmp_path: Path):
        conn = get_db(tmp_path)
        # Table exists
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit'"
        ).fetchone()
        assert row is not None
        conn.close()

    def test_creates_parent_dirs(self, tmp_path: Path):
        db_dir = tmp_path / "a" / "b"
        conn = get_db(db_dir)
        assert (db_dir / "audit.db").exists()
        conn.close()

    def test_idempotent_create(self, tmp_path: Path):
        conn1 = get_db(tmp_path)
        conn1.close()
        conn2 = get_db(tmp_path)
        conn2.close()


class TestLogResults:
    def test_write_entries(self, tmp_path: Path):
        results = [
            FakeResult("AC001", "case0001", "ok"),
            FakeResult("AC002", "case0002", "ok"),
        ]
        log_results(tmp_path, "myproject", results)

        conn = get_db(tmp_path)
        rows = conn.execute("SELECT * FROM audit").fetchall()
        assert len(rows) == 2
        conn.close()

    def test_append_multiple(self, tmp_path: Path):
        log_results(tmp_path, "proj", [FakeResult("AC001", "case0001", "ok")])
        log_results(tmp_path, "proj", [FakeResult("AC002", "case0002", "ok")])

        conn = get_db(tmp_path)
        rows = conn.execute("SELECT * FROM audit").fetchall()
        assert len(rows) == 2
        conn.close()

    def test_stores_error(self, tmp_path: Path):
        results = [
            FakeResult("AC001", "", "error", error="not found on PACS"),
        ]
        log_results(tmp_path, "proj", results)

        conn = get_db(tmp_path)
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        row = conn.execute("SELECT * FROM audit").fetchone()
        assert row["status"] == "error"
        assert row["error"] == "not found on PACS"
        conn.close()

    def test_stores_duration(self, tmp_path: Path):
        results = [FakeResult("AC001", "case0001", "ok", duration_s=12.5)]
        log_results(tmp_path, "proj", results)

        conn = get_db(tmp_path)
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        row = conn.execute("SELECT * FROM audit").fetchone()
        assert row["duration_s"] == 12.5
        conn.close()


class TestQueryAudit:
    def test_query_by_project(self, tmp_path: Path):
        log_results(tmp_path, "projA", [FakeResult("AC001", "case0001", "ok")])
        log_results(tmp_path, "projB", [FakeResult("AC002", "case0002", "ok")])

        rows = query_audit(tmp_path, project="projA")
        assert len(rows) == 1
        assert rows[0]["project"] == "projA"

    def test_query_all(self, tmp_path: Path):
        log_results(tmp_path, "projA", [FakeResult("AC001", "case0001", "ok")])
        log_results(tmp_path, "projB", [FakeResult("AC002", "case0002", "ok")])

        rows = query_audit(tmp_path)
        assert len(rows) == 2

    def test_query_last_limit(self, tmp_path: Path):
        for i in range(10):
            log_results(
                tmp_path, "proj", [FakeResult(f"AC{i:03d}", f"case{i:04d}", "ok")]
            )

        rows = query_audit(tmp_path, project="proj", last=3)
        assert len(rows) == 3
        # Should be the last 3 (highest IDs), returned in ascending order
        assert rows[0]["accession"] == "AC007"
        assert rows[2]["accession"] == "AC009"

    def test_query_empty(self, tmp_path: Path):
        rows = query_audit(tmp_path)
        assert rows == []

    def test_returns_dicts(self, tmp_path: Path):
        log_results(tmp_path, "proj", [FakeResult("AC001", "case0001", "ok")])
        rows = query_audit(tmp_path)
        assert isinstance(rows[0], dict)
        assert "timestamp" in rows[0]
        assert "operator" in rows[0]
        assert "accession" in rows[0]
