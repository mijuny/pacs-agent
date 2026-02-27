# pacs-agent

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Agent-first, PID-safe research image loader for hospital PACS.**

CLI tool: `rad-loader`

## The Problem

Loading DICOM images from hospital PACS for research is risky. Patient identifiers (names, IDs, birth dates) leak easily into research directories, logs, and AI agent outputs. Existing tools either skip anonymization entirely or treat it as an optional step.

pacs-agent solves this by making anonymization **mandatory and automatic**. There is no way to retrieve images without them being anonymized first. The tool is designed to be operated by AI agents (JSON output, structured errors, idempotent operations) while remaining usable by researchers directly.

## Architecture

```
Researcher / AI Agent
┌──────────────────┐
│ rad-loader       │
│ load project AC  │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ 1. C-FIND (accession → study UID)   │
│        ↓                             │
│ 2. Start temporary SCP (port 9012)   │
│        ↓                             │
│ 3. C-MOVE (study UID → our SCP)     │
│        ↓                             │
│    PACS sends C-STORE ──┐            │
│        ↓                │            │
│ 4. Receive + anonymize  │ ◀── mandatory, no bypass
│        ↓                │            │
│ 5. Save .dcm files      │            │
│        ↓                             │
│ 6. Update key.csv + audit log        │
│        ↓                             │
│ 7. Shut down SCP                     │
└──────────────────┬───────────────────┘
                   │ DICOM
         ┌─────────▼──────────┐
         │ Hospital PACS      │
         │ (any vendor)       │
         └────────────────────┘
```

**Key design choices:**
- **Allowlist anonymization** — only explicitly listed DICOM tags survive. Everything else is deleted.
- **No patient identifiers in I/O** — input is accession numbers only, output uses case IDs (case0001, case0002, ...).
- **Idempotent** — already-loaded studies are skipped automatically. Safe to re-run.
- **Audit trail** — every load is recorded in a SQLite database.

## Quick Start

### Install

```bash
git clone https://github.com/mijuny/pacs-agent.git
cd pacs-agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Configure

```bash
cp config/example.yaml config/config.yaml
# Edit config/config.yaml with your PACS connection details
```

Your PACS administrator needs to:
1. Register your AE title (e.g. `MY-LOADER`) on the PACS
2. Allow your host to connect
3. Open the SCP port (default 9012) in your firewall for incoming C-STORE from PACS

### Basic usage

```bash
# Test PACS connection
rad-loader echo

# Query a study (no images downloaded)
rad-loader query VAR9946804

# Load a study (download, anonymize, save)
rad-loader load myproject VAR9946804

# Load from file (one accession per line)
rad-loader load myproject --file accessions.txt

# Dry run (query only)
rad-loader load myproject --file accessions.txt --dry-run

# Check project status (includes outlier detection)
rad-loader status myproject

# View audit log
rad-loader audit myproject
```

## CLI Reference

```
rad-loader [--config CONFIG] [--human] [-v] {echo,query,load,status,audit}
```

**Global flags** (must come BEFORE the subcommand):

| Flag | Description |
|------|-------------|
| `--config PATH` | YAML config file (default: `config/config.yaml`) |
| `--human` | Human-readable output instead of JSON |
| `-v` | Verbose logging (DICOM-level traffic) |

### Commands

**echo** — Test PACS connection (C-ECHO)
```bash
rad-loader echo
```

**query** — Look up a study by accession number (C-FIND, no download)
```bash
rad-loader query <ACCESSION>
```

**load** — Download, anonymize, and save studies
```bash
rad-loader load <PROJECT> <AC1> [AC2 ...]
rad-loader load <PROJECT> --file <ACCESSION_FILE>
rad-loader load <PROJECT> --file <ACCESSION_FILE> --dry-run
```

**status** — Project statistics with outlier detection
```bash
rad-loader status <PROJECT>
```

**audit** — View audit log
```bash
rad-loader audit <PROJECT> [--last N]
rad-loader audit --all [--last N]
```

## Verification & Audit

### Load verification

Every `load` command returns a `verification` field:

```json
{
  "verification": {
    "ok": false,
    "total_requested": 10,
    "loaded": 7,
    "skipped": 1,
    "failed": 2,
    "not_found": 1,
    "warnings": ["AC001 (case0003): only 2 images (unusually low)"]
  }
}
```

### Outlier detection

The `status` command compares cases within a project:

```json
{
  "outliers": {
    "ok": false,
    "median_series": 5,
    "median_images": 450,
    "warnings": [
      "case0003: 1 series vs median 5 — possibly incomplete study",
      "case0009: modality CR differs from majority MR"
    ]
  }
}
```

### Audit log

All loads are recorded in a SQLite database with: Unix user, accession numbers, project name, timestamp, duration, and result.

## Anonymization

### Approach

pacs-agent uses an **allowlist** approach: only DICOM tags explicitly listed in the allowlist survive anonymization. All other tags — including unknown, private, and vendor-specific tags — are deleted. This is safer than a blocklist approach, where new or unexpected tags could slip through.

### What is removed (PHI)

| Field | DICOM Tag |
|-------|-----------|
| PatientName | (0010,0010) |
| PatientID | (0010,0020) |
| PatientBirthDate | (0010,0030) |
| OtherPatientIDs | (0010,1000) |
| OtherPatientNames | (0010,1001) |
| IssuerOfPatientID | (0010,0021) |
| PatientAddress | (0010,1040) |
| PatientTelephoneNumbers | (0010,2154) |
| AdditionalPatientHistory | (0010,21B0) |
| PatientComments | (0010,4000) |
| ReferringPhysicianName | (0008,0090) |
| PerformingPhysicianName | (0008,1050) |
| OperatorsName | (0008,1070) |
| RequestingPhysician | (0032,1032) |
| InstitutionName | (0008,0080) |
| InstitutionAddress | (0008,0081) |
| RequestAttributesSequence | (0040,0275) |
| All private tags | Odd group numbers |
| All unknown tags | Not on allowlist |

### What is preserved

| Category | Examples |
|----------|----------|
| Identifiers (non-PID) | AccessionNumber, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID |
| Study metadata | StudyDate, Modality, StudyDescription, SeriesDescription |
| Demographics | PatientSex, PatientAge, PatientSize, PatientWeight |
| MR parameters | RepetitionTime, EchoTime, FlipAngle, MagneticFieldStrength, SliceThickness, DiffusionBValue, ... |
| CT parameters | KVP, ExposureTime, XRayTubeCurrent, ConvolutionKernel, ... |
| General acquisition | ProtocolName, BodyPartExamined, ContrastBolusAgent, PatientPosition |
| Pixel description | Rows, Columns, PixelSpacing, BitsAllocated, WindowCenter/Width, RescaleSlope/Intercept |
| Spatial geometry | ImagePositionPatient, ImageOrientationPatient, SliceLocation, FrameOfReferenceUID |
| Equipment | Manufacturer, ManufacturerModelName, SoftwareVersions, DeviceSerialNumber |
| Pixel data | PixelData (the actual image) |

### What is set after anonymization

| Field | Value |
|-------|-------|
| PatientName | Case ID (e.g. `case0001`) |
| PatientID | Case ID |
| PatientIdentityRemoved | `YES` |
| DeidentificationMethod | `pacs-agent allowlist v1` |

### Limitations

- **Burned-in annotations** in pixel data are NOT removed. Review images manually.
- **Structured Reports** (SR) are not anonymized — they are skipped.
- **Single-threaded**: one study at a time via C-MOVE.
- **Temporary SCP**: the receive port is open only during the load.

## Agent Integration

pacs-agent is designed to be operated by AI agents (Claude Code, etc.). All commands output structured JSON by default.

### CLAUDE.md template

Add this to your project's `CLAUDE.md` to teach Claude Code how to use rad-loader. See [CLAUDE.md](CLAUDE.md) in this repository for a ready-to-use template.

### Accession file format

Plain text, one accession number per line. Empty lines and `#` comments are allowed:

```
# Brain hemorrhage study, spring 2026
VAR9946804
VAR9946805

# Control patients
VAR9946810
VAR9946811
```

## Configuration

See [config/example.yaml](config/example.yaml):

```yaml
pacs:
  host: "pacs.example.com"        # PACS host IP or hostname
  port: 104                       # PACS port (standard DICOM)
  ae_title: "YOUR_PACS"           # PACS AE title (called AE)

scp:
  ae_title: "MY-LOADER"           # Our AE title (calling AE / SCP)
  port: 9012                      # Port for incoming C-STORE

output:
  base_dir: "/data/research"      # Base output directory
```

Copy to `config/config.yaml` and fill in your values. All `.yaml` files except `example.yaml` are gitignored.

## Output Structure

```
<output_base_dir>/
├── audit.db                    # Global audit database (SQLite)
├── <project>/
│   ├── key.csv                 # case_id,accession,study_date,modality,description,series_count,image_count
│   ├── load.json               # Machine-readable load summary
│   ├── case0001/
│   │   ├── series01/*.dcm
│   │   ├── series02/*.dcm
│   │   └── ...
│   └── case0002/
│       └── ...
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

Tests that require DICOM sample files are automatically skipped in CI. To run the full test suite locally, place [DICOM WG-04 reference files](https://www.dclunie.com/pixelmed/software/webstart/DicomImageViewer.html) in `~/projects/dicom-test-files/data/WG04/REF/` as `.zst` archives.

## Finnish Guide

A researcher-oriented guide in Finnish is available at [GUIDE_FI.md](GUIDE_FI.md).

## Contributing

Contributions are welcome. Please open an issue first to discuss what you'd like to change.

## Citation

If you use pacs-agent in your research, please cite:

```bibtex
@software{pacs_agent,
  author = {Nyman, Mikko},
  title = {pacs-agent: Agent-first, PID-safe research image loader for hospital PACS},
  url = {https://github.com/mijuny/pacs-agent},
  year = {2026}
}
```

## License

This work is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). You are free to use and adapt it for non-commercial purposes with attribution.
