"""Audit logging — SQLite database at base_dir/audit.db."""

from __future__ import annotations

import getpass
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def get_db(base_dir: Path) -> sqlite3.Connection:
    """Open (and create if needed) the audit database."""
    db_path = base_dir / "audit.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE IF NOT EXISTS audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        operator TEXT NOT NULL,
        project TEXT NOT NULL,
        accession TEXT NOT NULL,
        case_id TEXT,
        status TEXT NOT NULL,
        modality TEXT,
        image_count INTEGER,
        series_count INTEGER,
        duration_s REAL,
        error TEXT
    )""")
    conn.commit()
    return conn


def log_results(
    base_dir: Path, project: str, results: list, dry_run: bool = False,
) -> None:
    """Write one row per result to audit table."""
    conn = get_db(base_dir)
    operator = getpass.getuser()
    timestamp = datetime.now(timezone.utc).isoformat()
    for r in results:
        conn.execute(
            "INSERT INTO audit"
            " (timestamp,operator,project,accession,case_id,status,"
            "modality,image_count,series_count,duration_s,error)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                timestamp,
                operator,
                project,
                r.accession,
                r.case_id or None,
                r.status,
                r.modality or None,
                r.image_count,
                r.series_count,
                r.duration_s,
                r.error,
            ),
        )
    conn.commit()
    conn.close()


def query_audit(
    base_dir: Path, project: str | None = None, last: int = 20,
) -> list[dict]:
    """Read audit entries. Filter by project if given."""
    conn = get_db(base_dir)
    conn.row_factory = sqlite3.Row
    if project:
        rows = conn.execute(
            "SELECT * FROM audit WHERE project=? ORDER BY id DESC LIMIT ?",
            (project, last),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (last,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]
