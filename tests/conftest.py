"""Shared test fixtures."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

DICOM_TEST_DIR = Path.home() / "projects" / "dicom-test-files" / "data" / "WG04"
REF_DIR = DICOM_TEST_DIR / "REF"

requires_dicom_files = pytest.mark.skipif(
    not REF_DIR.exists(),
    reason=f"DICOM test files not found at {REF_DIR}",
)


def _decompress_zst(zst_path: Path, out_path: Path) -> Path:
    """Decompress a .zst file if the output doesn't exist."""
    if not out_path.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["zstd", "-d", str(zst_path), "-o", str(out_path)],
            check=True,
            capture_output=True,
        )
    return out_path


@pytest.fixture(scope="session")
def tmp_dcm_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Decompress test DICOM files into a temp directory."""
    if not REF_DIR.exists():
        pytest.skip(f"DICOM test files not found at {REF_DIR}")
    out = tmp_path_factory.mktemp("dcm")
    for zst in sorted(REF_DIR.glob("*.zst")):
        name = zst.stem  # e.g. CT1_UNC
        _decompress_zst(zst, out / f"{name}.dcm")
    return out


@pytest.fixture(scope="session")
def ct1_path(tmp_dcm_dir: Path) -> Path:
    return tmp_dcm_dir / "CT1_UNC.dcm"


@pytest.fixture(scope="session")
def mr1_path(tmp_dcm_dir: Path) -> Path:
    return tmp_dcm_dir / "MR1_UNC.dcm"
