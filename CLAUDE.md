# rad-loader — Agent Instructions

## What this tool does

`rad-loader` loads anonymized DICOM images from hospital PACS for research. It is **PID-safe by design** — no patient names, IDs, or birth dates ever appear in output, logs, or saved files.

## Available commands

All commands run on **ahjo** via SSH:

```bash
# Test PACS connection
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader echo"

# Query a study by accession number (returns JSON, no images downloaded)
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader query <ACCESSION>"

# Load studies (downloads, anonymizes, saves to /data/research/<project>/)
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader load <project> <AC1> <AC2> ..."

# Load from file (one accession per line, # comments allowed)
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader load <project> --file <path>"

# Dry run (query only, no download)
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader load <project> --file <path> --dry-run"

# Check project status (includes outlier detection)
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader status <project>"

# View audit log for a project
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader audit <project>"
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader audit <project> --last 50"

# View all audit entries (cross-project)
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader audit --all"
```

## Important rules

- **Input**: Only accession numbers (e.g. `VAR9946804`). Never use patient names or IDs.
- **Output**: JSON by default. Add `--human` before the subcommand for readable output.
- **Global flags** (`--human`, `-v`, `--config`) go BEFORE the subcommand.
- **Already loaded** studies are automatically skipped — safe to re-run.
- **Output location**: `/data/research/<project>/` on ahjo.
- **key.csv** maps case IDs (case0001, case0002, ...) to accession numbers.

## Troubleshooting

If a load fails or behaves unexpectedly, re-run with `-v` (verbose) for detailed DICOM-level logging including pydicom validation warnings and pynetdicom network traffic:

```bash
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader -v load <project> <AC>"
```

Without `-v`, pydicom/pynetdicom warnings are suppressed to keep output clean.

## Output structure

```
/data/research/
├── audit.db                    # Global audit database (SQLite)
├── <project>/
│   ├── key.csv                 # case_id,accession,study_date,modality,description,series_count,image_count
│   ├── load.json               # Machine-readable load summary (includes verification)
│   ├── case0001/
│   │   ├── series01/*.dcm
│   │   ├── series02/*.dcm
│   │   └── ...
│   └── case0002/
│       └── ...
└── <other-project>/
    └── ...
```

## Verification after loading

### Step 1: Check load results
The `load` command output includes a `verification` field. Check it:
- `not_found` > 0: accessions not in PACS — check for typos, ask researcher
- `failed` > 0: PACS errors — retry failed accessions
- `warnings`: unusual image counts — flag to researcher

### Step 2: Check for outliers across cases
Run `rad-loader status PROJECT` and check the `outliers` field:
- Cases with significantly fewer series than others — possibly incomplete study
- Cases with much fewer/more images than median — investigate
- Modality mismatches — wrong study may have been loaded

### Step 3: Report to researcher
Always present a summary:
- X of Y accessions loaded successfully
- N skipped (already loaded)
- Any failures or warnings
- Any outlier cases that need attention
- If issues found, ask researcher how to proceed before continuing

## What is preserved in anonymized files

- AccessionNumber, StudyInstanceUID, SeriesInstanceUID
- StudyDate, Modality, StudyDescription, SeriesDescription
- PatientSex, PatientAge, PatientSize, PatientWeight
- All acquisition parameters (TR, TE, flip angle, slice thickness, kVp, mAs, etc.)
- Pixel data, spatial geometry, window/level settings
- Manufacturer, model, software version

## What is removed

- Patient name, ID, birth date, address, phone
- Physician names (referring, performing, requesting, operators)
- Institution name and address
- All private/vendor tags
- All unknown tags not on the allowlist

## Limitations

- Burned-in annotations in pixel data are NOT removed
- Single-threaded: one study at a time
- Large studies (1000+ images) take 1-2 minutes
