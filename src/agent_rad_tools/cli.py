"""CLI entry point for rad-loader.

Usage:
    rad-loader echo
    rad-loader query ACCESSION
    rad-loader load PROJECT AC1 AC2 ...
    rad-loader load PROJECT --file accessions.txt
    rad-loader status PROJECT
    rad-loader audit PROJECT [--last N]
    rad-loader audit --all [--last N]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .config import Config
from .keyfile import read_key_file


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="rad-loader",
        description="PID-safe research image loader for hospital PACS",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/ahjo.yaml"),
        help="Path to YAML config file (default: config/ahjo.yaml)",
    )
    parser.add_argument(
        "--human",
        action="store_true",
        help="Human-readable output (default: JSON)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # echo
    sub.add_parser("echo", help="Test PACS connection (C-ECHO)")

    # query
    p_query = sub.add_parser("query", help="Query accession number (C-FIND)")
    p_query.add_argument("accession", help="Accession number to query")

    # load
    p_load = sub.add_parser("load", help="Load studies from PACS")
    p_load.add_argument("project", help="Project name")
    p_load.add_argument("accessions", nargs="*", help="Accession numbers")
    p_load.add_argument(
        "--file", "-f",
        type=Path,
        dest="accession_file",
        help="File with accession numbers (one per line)",
    )
    p_load.add_argument(
        "--dry-run",
        action="store_true",
        help="Query only, don't retrieve images",
    )

    # status
    p_status = sub.add_parser("status", help="Check project status")
    p_status.add_argument("project", help="Project name")

    # audit
    p_audit = sub.add_parser("audit", help="View audit log")
    p_audit.add_argument("project", nargs="?", help="Project name (omit with --all)")
    p_audit.add_argument(
        "--all", action="store_true", dest="all_projects",
        help="Show all projects",
    )
    p_audit.add_argument(
        "--last", type=int, default=20,
        help="Number of entries to show (default: 20)",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    # Suppress pynetdicom/pydicom verbose logging unless -v
    if not args.verbose:
        logging.getLogger("pynetdicom").setLevel(logging.WARNING)
        logging.getLogger("pydicom").setLevel(logging.ERROR)

    if args.command == "echo":
        _cmd_echo(args)
    elif args.command == "query":
        _cmd_query(args)
    elif args.command == "load":
        _cmd_load(args)
    elif args.command == "status":
        _cmd_status(args)
    elif args.command == "audit":
        _cmd_audit(args)


def _load_config(args: argparse.Namespace) -> Config:
    config_path = args.config
    if not config_path.exists():
        _error(f"Config file not found: {config_path}")
    return Config.from_file(config_path)


def _output(data: dict | list, human: bool) -> None:
    """Print output as JSON or human-readable."""
    if human:
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    print(f"\n{k}:")
                    for item in v:
                        if isinstance(item, dict):
                            for ik, iv in item.items():
                                print(f"  {ik}: {iv}")
                            print()
                        else:
                            print(f"  {item}")
                else:
                    print(f"{k}: {v}")
        else:
            print(json.dumps(data, indent=2))
    else:
        json.dump(data, sys.stdout, indent=2)
        print()


def _error(msg: str) -> None:
    print(json.dumps({"status": "error", "error": msg}))
    sys.exit(1)


def _cmd_echo(args: argparse.Namespace) -> None:
    from .pacs import echo

    config = _load_config(args)
    result = echo(config)
    _output(
        {
            "status": "ok" if result else "error",
            "pacs": f"{config.pacs.host}:{config.pacs.port}",
            "ae_title": config.pacs.ae_title,
            "echo": "success" if result else "failed",
        },
        args.human,
    )
    if not result:
        sys.exit(1)


def _cmd_query(args: argparse.Namespace) -> None:
    from .pacs import find_by_accession

    config = _load_config(args)
    studies = find_by_accession(config, args.accession)
    _output(
        {
            "status": "ok",
            "accession": args.accession,
            "results": studies,
        },
        args.human,
    )


def _cmd_load(args: argparse.Namespace) -> None:
    from .loader import load_studies, result_to_dict

    config = _load_config(args)

    accessions = list(args.accessions or [])
    if args.accession_file:
        if not args.accession_file.exists():
            _error(f"Accession file not found: {args.accession_file}")
        text = args.accession_file.read_text()
        accessions.extend(
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    if not accessions:
        _error("No accession numbers provided")

    results, verification = load_studies(
        config, args.project, accessions, dry_run=args.dry_run
    )

    _output(
        {
            "status": "ok",
            "project": args.project,
            "results": [result_to_dict(r) for r in results],
            "verification": verification,
        },
        args.human,
    )


def _cmd_status(args: argparse.Namespace) -> None:
    from .verify import verify_project

    config = _load_config(args)
    project_dir = config.output.base_dir / args.project
    key_path = project_dir / "key.csv"

    if not project_dir.exists():
        _output(
            {
                "status": "ok",
                "project": args.project,
                "exists": False,
                "cases": 0,
            },
            args.human,
        )
        return

    entries = read_key_file(key_path)
    total_images = sum(e.image_count for e in entries)
    outliers = verify_project(entries)

    _output(
        {
            "status": "ok",
            "project": args.project,
            "exists": True,
            "cases": len(entries),
            "total_images": total_images,
            "entries": [
                {
                    "case_id": e.case_id,
                    "accession": e.accession,
                    "study_date": e.study_date,
                    "modality": e.modality,
                    "description": e.description,
                    "series_count": e.series_count,
                    "image_count": e.image_count,
                }
                for e in entries
            ],
            "outliers": outliers,
        },
        args.human,
    )


def _cmd_audit(args: argparse.Namespace) -> None:
    from .audit import query_audit

    config = _load_config(args)

    if not args.project and not args.all_projects:
        _error("Specify a project name or use --all")

    project = args.project if not args.all_projects else None
    entries = query_audit(config.output.base_dir, project=project, last=args.last)

    _output(
        {
            "status": "ok",
            "entries": entries,
        },
        args.human,
    )


if __name__ == "__main__":
    main()
