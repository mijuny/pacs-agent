"""YAML configuration loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PacsConfig:
    host: str
    port: int
    ae_title: str  # PACS AE title (called AE)


@dataclass
class ScpConfig:
    ae_title: str = "AHJO-loader"  # Our AE title
    port: int = 9012


@dataclass
class OutputConfig:
    base_dir: Path = field(default_factory=lambda: Path("/data/research"))


@dataclass
class Config:
    pacs: PacsConfig
    scp: ScpConfig
    output: OutputConfig

    @classmethod
    def from_file(cls, path: Path) -> Config:
        with open(path) as f:
            raw = yaml.safe_load(f)

        pacs_raw = raw.get("pacs", {})
        pacs = PacsConfig(
            host=pacs_raw["host"],
            port=int(pacs_raw["port"]),
            ae_title=pacs_raw["ae_title"],
        )

        scp_raw = raw.get("scp", {})
        scp = ScpConfig(
            ae_title=scp_raw.get("ae_title", "AHJO-loader"),
            port=int(scp_raw.get("port", 9012)),
        )

        out_raw = raw.get("output", {})
        output = OutputConfig(
            base_dir=Path(out_raw.get("base_dir", "/data/research")),
        )

        return cls(pacs=pacs, scp=scp, output=output)
