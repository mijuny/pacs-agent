#!/bin/bash
# Wrapper for researchers to load studies from PACS.
# Usage: ./researcher-load.sh <project> <accession-file>
#
# This script is the intended interface for researchers.
# Adjust LOADER path to your installation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOADER="${SCRIPT_DIR}/../.venv/bin/rad-loader"

if [ ! -x "$LOADER" ]; then
    echo "Error: rad-loader not found at $LOADER"
    echo "Install: cd $(dirname "$SCRIPT_DIR") && python -m venv .venv && .venv/bin/pip install -e ."
    exit 1
fi

usage() {
    echo "Usage:"
    echo "  $0 echo                          # Test PACS connection"
    echo "  $0 query <accession>             # Query single study"
    echo "  $0 load <project> <file>         # Load studies from file"
    echo "  $0 load <project> <file> --dry-run  # Preview without loading"
    echo "  $0 status <project>              # Check project status"
    exit 1
}

[ $# -lt 1 ] && usage

case "$1" in
    echo)
        exec "$LOADER" --human echo
        ;;
    query)
        [ $# -lt 2 ] && { echo "Error: accession number required"; exit 1; }
        exec "$LOADER" --human query "$2"
        ;;
    load)
        [ $# -lt 3 ] && { echo "Error: project name and accession file required"; exit 1; }
        project="$2"
        file="$3"
        shift 3
        [ ! -f "$file" ] && { echo "Error: file not found: $file"; exit 1; }
        echo "Project: $project"
        echo "Accessions: $file ($(grep -cv '^#\|^$' "$file" || true) entries)"
        echo ""
        exec "$LOADER" --human load "$project" --file "$file" "$@"
        ;;
    status)
        [ $# -lt 2 ] && { echo "Error: project name required"; exit 1; }
        exec "$LOADER" --human status "$2"
        ;;
    *)
        usage
        ;;
esac
