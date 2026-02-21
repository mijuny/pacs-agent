# agent-rad-tools

AI-agentin DICOM- ja tietokantavälineet sairaalaympäristöön. PID-turvallinen by design.

## Perusperiaate

Nämä työkalut on suunniteltu AI-agentin käyttöön. Agentti **ei koskaan näe potilastietoja** (PID).
Tämä ei ole anonymisointia — PID-kenttiä ei palauteta ollenkaan. Allowlist, ei blocklist.

### Input-rajoitus
- Toolit hyväksyvät VAIN ei-PID-tunnisteita: Accession Number, Study/Series/SOP Instance UID
- `--patient-name` ja `--patient-id` parametreja EI OLE
- Virheellinen input → hylätään ennen DICOM/SQL-kutsua

### Output-rajoitus
- JSON-output rakennetaan EXPLICIT allowlistillä
- PID-kentät (PatientName, PatientID, PatientBirthDate, jne.) eivät ole allowlistillä
- Ei koskaan serialisoida PID:tä — ei stdouttiin, ei logeihin, ei virheviesteihin

### Processing
- PACS palauttaa PID:n sisäisesti — se käsitellään muistissa mutta ei vuoda ulos
- Virheviestit viittaavat vain AC/UID-tunnisteisiin

## Toolit

### DICOM

| Tool | Operaatio | Kuvaus |
|------|-----------|--------|
| `dicom-echo` | C-ECHO | Testaa PACS-yhteys |
| `dicom-query` | C-FIND | Hae tutkimuksia AC/UID:llä |
| `dicom-move` | C-MOVE | Siirrä tutkimus PACSien välillä |
| `dicom-status` | C-FIND | Tutkimuksen tila ja metadata |

### SQL

| Tool | Kuvaus |
|------|--------|
| `sql-query` | Lue tietokantoja allowlist-sarakkeilla |

### Monitoring

| Tool | Kuvaus |
|------|--------|
| `service-check` | Palvelinten tila, DICOM-yhteydet |
| `storage-check` | Levytilat, PACS-kapasiteetti |

## Output-formaatti

Kaikki toolit palauttavat JSON:ia stdouttiin:

```json
{
  "status": "ok",
  "tool": "dicom-query",
  "results": [
    {
      "accession": "12345678",
      "studyUID": "1.2.840.113619...",
      "modality": "MR",
      "studyDate": "2026-02-21",
      "studyDescription": "MRI Brain",
      "seriesCount": 3,
      "imageCount": 187
    }
  ]
}
```

## Allowlist-kentät

### DICOM Study-taso
- AccessionNumber
- StudyInstanceUID
- Modality / ModalitiesInStudy
- StudyDate, StudyTime
- StudyDescription
- NumberOfStudyRelatedSeries
- NumberOfStudyRelatedInstances
- InstitutionName
- ReferringPhysicianName ← HUOM: tämä voi olla PID-rajamailla, päätetään myöhemmin
- StudyStatusID (jos PACS tukee)

### DICOM Series-taso
- SeriesInstanceUID
- SeriesNumber
- SeriesDescription
- Modality
- NumberOfSeriesRelatedInstances
- BodyPartExamined

### SQL
- Per-tietokanta schema-tiedosto määrittelee sallitut sarakkeet
- Oletus: kaikki sarakkeet jotka eivät sisällä PID:tä (nimi, hetu, syntymäaika, osoite, puhelin)

## Tech stack

- **Kieli:** Python 3.11+
- **DICOM:** pynetdicom + pydicom
- **SQL:** SQLAlchemy (read-only)
- **Output:** JSON (stdout)
- **Config:** YAML (PACS-nodet, AE-titlet, tietokantayhteydet)

## Konfiguraatio

```yaml
# config.yaml
pacs:
  main:
    ae_title: "AGENT_RAD"
    host: "pacs1.hospital.local"
    port: 104
    peer_ae: "PACS1"
  archive:
    ae_title: "AGENT_RAD"
    host: "pacs2.hospital.local"
    port: 104
    peer_ae: "PACS_ARCHIVE"

databases:
  ris:
    url: "postgresql://readonly@ris.hospital.local/ris"
    schema: "schemas/ris.yaml"

logging:
  audit: true        # kuka kutsui, milloin, millä parametreilla
  pid_in_logs: false  # AINA false — logit ei sisällä PID:tä
```

## Asennus

```bash
cd ~/projects/agent-rad-tools
python -m venv .venv
source .venv/bin/activate
pip install pynetdicom pydicom sqlalchemy pyyaml
```

## Lisenssi

Sisäinen työkalu — TYKS Kuvantaminen
