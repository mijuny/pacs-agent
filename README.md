# rad-loader

PID-turvallinen tutkimuskuvien lataaja sairaalan PACS-järjestelmästä. Hakee DICOM-tutkimuksia accession-numerolla, anonymisoi ja tallentaa tutkimusprojektin hakemistoon.

## Pikaohje tutkijalle

### Mitä tarvitset

1. **Accession-numerot** tutkimuksista jotka haluat ladata (esim. RIS:stä tai tutkimusrekisteristä)
2. **SSH-yhteys ahjo-palvelimelle** (t480-ahjo, sairaalan verkossa)
3. **Projektinimi** tutkimuksellesi (esim. `aivoverenvuoto-2026`, `ms-seuranta`)

### Latausprosessi

```bash
# 1. Yhdistä ahjoon
ssh ahjo

# 2. Tarkista PACS-yhteys
/data/apps/agent-rad-tools/.venv/bin/rad-loader echo

# 3. Tarkista yksittäinen tutkimus (ei lataa kuvia)
/data/apps/agent-rad-tools/.venv/bin/rad-loader query VAR9946804

# 4. Lataa yksittäinen tutkimus
/data/apps/agent-rad-tools/.venv/bin/rad-loader load projektini VAR9946804

# 5. Lataa useita kerralla
/data/apps/agent-rad-tools/.venv/bin/rad-loader load projektini VAR9946804 VAR9946805 VAR9946806

# 6. Lataa tiedostosta (yksi accession per rivi)
/data/apps/agent-rad-tools/.venv/bin/rad-loader load projektini --file accession_lista.txt

# 7. Kuivaharjoittelu (näyttää mitä ladattaisiin, ei lataa)
/data/apps/agent-rad-tools/.venv/bin/rad-loader load projektini --file accession_lista.txt --dry-run

# 8. Tarkista projektin tila (sis. poikkeamien tunnistus)
/data/apps/agent-rad-tools/.venv/bin/rad-loader status projektini

# 9. Tarkista auditointiloki
/data/apps/agent-rad-tools/.venv/bin/rad-loader audit projektini
/data/apps/agent-rad-tools/.venv/bin/rad-loader audit --all
```

### Tulos

Kuvat tallentuvat hakemistoon `/data/research/projektini/`:

```
/data/research/
├── audit.db                        # Globaali auditointitietokanta (SQLite)
├── projektini/
│   ├── key.csv                     # Avaintiedosto: case_id → accession + metadata
│   ├── load.json                   # Koneluettava latausyhteenveto (sis. verifiointi)
│   ├── case0001/
│   │   ├── series01/
│   │   │   ├── 00001.dcm
│   │   │   ├── 00002.dcm
│   │   │   └── ...
│   │   ├── series02/
│   │   │   └── ...
│   │   └── ...
│   ├── case0002/
│   │   └── ...
│   └── ...
└── toinen-projekti/
    └── ...
```

- Jokainen tutkimus saa juoksevan tunnisteen (`case0001`, `case0002`, ...)
- `key.csv` yhdistää tunnisteen accession-numeroon, modaliteettiin ja päivämäärään
- Jo ladatut tutkimukset ohitetaan automaattisesti (voi ajaa uudestaan turvallisesti)

### Accession-listan formaatti

Tekstitiedosto, yksi accession per rivi. Tyhjät rivit ja `#`-kommentit sallitaan:

```
# Aivoverenvuoto-tutkimus, kevät 2026
VAR9946804
VAR9946805

# Kontrollipotilaat
VAR9946810
VAR9946811
```

## Ohjeet AI-agentille

Jos käytät Claude Code -agenttia tai muuta AI-työkalua tutkimuskuvien lataamiseen:

### Peruskäyttö

```bash
# Testaa yhteys
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader echo"

# Hae tutkimuksen tiedot (JSON)
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader query VAR9946804"

# Lataa tutkimuksia
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader load projekti AC1 AC2 AC3"

# Tarkista tila (sis. poikkeamien tunnistus)
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader status projekti"

# Auditointiloki
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader audit projekti"
ssh ahjo "/data/apps/agent-rad-tools/.venv/bin/rad-loader audit --all --last 50"
```

### JSON-output

Kaikki komennot tulostavat JSON:ia (koneluettava). Oletusoutput:

```json
{
  "status": "ok",
  "accession": "VAR9946804",
  "results": [
    {
      "AccessionNumber": "VAR9946804",
      "StudyInstanceUID": "1.2.246.10.8541653.92001.9946804",
      "ModalitiesInStudy": "MR",
      "StudyDate": "20260223",
      "StudyDescription": "Pään MT",
      "NumberOfStudyRelatedSeries": "18",
      "NumberOfStudyRelatedInstances": "1447",
      "PatientSex": "F",
      "PatientAge": "076Y"
    }
  ]
}
```

### Ihmisluettava output

Lisää `--human` ennen komentoa:

```bash
rad-loader --human echo
rad-loader --human query VAR9946804
rad-loader --human status projekti
```

### Verbose-tila

Lisää `-v` ennen komentoa (näyttää DICOM-liikenteen):

```bash
rad-loader -v load projekti VAR9946804
```

### Työnkulku tutkimusprojektissa

1. Tutkija toimittaa accession-listan (esim. CSV:stä poimittu sarake)
2. Tallenna lista tiedostoon ahjo-palvelimella
3. Aja `rad-loader load projektinimi --file lista.txt --dry-run` — tarkista mitä löytyy
4. Aja `rad-loader load projektinimi --file lista.txt` — lataa ja anonymisoi
5. Kuvat ovat valmiina hakemistossa `/data/research/projektinimi/`
6. `key.csv` kertoo mikä case vastaa mitäkin accession-numeroa

## Verifiointi ja auditointi

### Latauksen verifiointi

Jokainen `load`-komento palauttaa `verification`-kentän:

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

- `not_found`: accession-numeroa ei löydy PACS:sta (kirjoitusvirhe?)
- `failed`: PACS-virhe (yritä uudelleen)
- `warnings`: epätavallinen kuvamäärä (< 5 tai > 5000)

### Projektin poikkeamien tunnistus

`status`-komento vertaa projektin tapauksia toisiinsa ja palauttaa `outliers`-kentän:

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

### Auditointiloki

Kaikki lataukset kirjataan SQLite-tietokantaan (`/data/research/audit.db`):
- Kuka latasi (Unix-käyttäjä)
- Mitä accession-numeroita
- Mihin projektiin
- Milloin ja miten kauan kesti
- Onnistuiko vai epäonnistuiko

```bash
# Projektin auditointiloki
rad-loader audit projektini

# Kaikki projektit
rad-loader audit --all

# Viimeiset 50 merkintää
rad-loader audit --all --last 50
```

## Anonymisointi

### Mitä poistetaan (PHI)

| Kenttä | DICOM-tagi |
|--------|------------|
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
| Kaikki yksityiset tagit | Parittomat ryhmänumerot |
| Kaikki tuntemattomat tagit | Ei allowlistillä |

### Mitä säilytetään

| Kategoria | Esimerkkejä |
|-----------|-------------|
| Tunnisteet (ei-PID) | AccessionNumber, StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID |
| Tutkimustiedot | StudyDate, StudyTime, Modality, StudyDescription, SeriesDescription |
| Demografiat | PatientSex, PatientAge, PatientSize, PatientWeight |
| Kuvausparametrit (MR) | RepetitionTime, EchoTime, FlipAngle, MagneticFieldStrength, SliceThickness, PixelBandwidth, AcquisitionMatrix, DiffusionBValue, ... |
| Kuvausparametrit (CT) | KVP, ExposureTime, XRayTubeCurrent, ConvolutionKernel, ... |
| Kuvausparametrit (yleiset) | ProtocolName, BodyPartExamined, ContrastBolusAgent, PatientPosition |
| Pikselitiedot | Rows, Columns, PixelSpacing, BitsAllocated, BitsStored, WindowCenter/Width, RescaleSlope/Intercept |
| Sijainti/geometria | ImagePositionPatient, ImageOrientationPatient, SliceLocation, FrameOfReferenceUID |
| Laitteisto | Manufacturer, ManufacturerModelName, SoftwareVersions, DeviceSerialNumber |
| Pikselidata | PixelData (varsinainen kuva) |

### Mitä asetetaan anonymisoinnin jälkeen

| Kenttä | Arvo |
|--------|------|
| PatientName | case-tunnus (esim. `case0001`) |
| PatientID | case-tunnus |
| PatientIdentityRemoved | `YES` |
| DeidentificationMethod | `agent-rad-tools allowlist v1` |

### Rajoitukset

- **Burned-in annotations**: Kuviin poltetut tekstit (esim. potilaan nimi röntgenkuvassa) EI poistu. Tarkista kuvat manuaalisesti.
- **Structured Reports**: SR-objekteja ei anonymisoida — ne ohitetaan tai poistetaan.
- **Yksisäikeinen**: Tutkimukset ladataan yksi kerrallaan (C-MOVE).
- **Väliaikainen SCP**: Portti 9012 on auki vain latauksen ajan.

## Tekninen arkkitehtuuri

```
Tutkija/Agentti                      ahjo (192.168.186.156)
┌──────────────┐                    ┌──────────────────────────────────┐
│ rad-loader   │───SSH──────────────│ 1. C-FIND (accession → UID)     │
│ load ...     │                    │        ↓                        │
│              │                    │ 2. Käynnistä SCP (portti 9012)  │
│              │                    │        ↓                        │
│              │                    │ 3. C-MOVE (UID → AHJO-loader)   │
│              │                    │        ↓                        │
│              │                    │    PACS lähettää C-STORE ──┐    │
│              │                    │        ↓                   │    │
│              │                    │ 4. Vastaanota + anonymisoi │    │
│              │                    │        ↓                   │    │
│              │                    │ 5. Tallenna .dcm           │    │
│              │                    │        ↓                        │
│              │                    │ 6. Päivitä key.csv              │
│              │                    │        ↓                        │
│              │                    │ 7. Sammuta SCP                  │
└──────────────┘                    └──────────────────────────────────┘
                                              ↕ DICOM
                                    ┌──────────────────────┐
                                    │ Carestream PACS      │
                                    │ 193.143.202.115:104  │
                                    │ AET: med_imFIR       │
                                    └──────────────────────┘
```

## Asennus (kehittäjille)

```bash
cd ~/projects/agent-rad-tools
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Testit
pytest tests/ -v
```

### Konfiguraatio

Kopioi `config/example.yaml` → `config/ahjo.yaml` ja täytä oikeat arvot:

```yaml
pacs:
  host: "193.143.202.115"
  port: 104
  ae_title: "med_imFIR"

scp:
  ae_title: "AHJO-loader"
  port: 9012

output:
  base_dir: "/data/research"
```

### Deployaus ahjoon

```bash
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
  ~/projects/agent-rad-tools/ ahjo:/data/apps/agent-rad-tools/
ssh ahjo "cd /data/apps/agent-rad-tools && python3 -m venv .venv && .venv/bin/pip install -e ."
```

### Palomuurisäännöt (ahjo)

PACS tarvitsee yhteyden porttiin 9012 lähettääkseen kuvat:

```bash
sudo ufw allow from 193.143.0.0/16 to any port 9012 proto tcp comment 'PACS C-STORE'
```

## CLI-referenssi

```
rad-loader [--config CONFIG] [--human] [-v] {echo,query,load,status,audit}

Yleiset valinnat:
  --config PATH    YAML-konfiguraatio (oletus: config/ahjo.yaml)
  --human          Ihmisluettava output (oletus: JSON)
  -v               Verbose (DICOM-liikenteen yksityiskohdat)

Komennot:
  echo                          Testaa PACS-yhteys (C-ECHO)
  query ACCESSION               Hae tutkimuksen tiedot (C-FIND)
  load PROJEKTI AC [AC ...]     Lataa tutkimuksia
  load PROJEKTI --file LISTA    Lataa listasta
  load PROJEKTI --file LISTA --dry-run   Kuivaharjoittelu
  status PROJEKTI               Projektin tila, tilastot ja poikkeamat
  audit PROJEKTI [--last N]     Auditointiloki projektille
  audit --all [--last N]        Auditointiloki kaikille projekteille
```

## Lisenssi

Sisäinen työkalu — TYKS Kuvantaminen
