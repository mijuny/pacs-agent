# rad-loader — Pikaohje tutkijalle

PID-turvallinen tutkimuskuvien lataaja sairaalan PACS-järjestelmästä. Hakee DICOM-tutkimuksia accession-numerolla, anonymisoi ja tallentaa tutkimusprojektin hakemistoon.

## Mitä tarvitset

1. **Accession-numerot** tutkimuksista jotka haluat ladata (esim. RIS:stä tai tutkimusrekisteristä)
2. **Pääsy palvelimelle** jolla rad-loader on asennettu
3. **Projektinimi** tutkimuksellesi (esim. `aivoverenvuoto-2026`, `ms-seuranta`)

## Latausprosessi

```bash
# 1. Tarkista PACS-yhteys
rad-loader echo

# 2. Tarkista yksittäinen tutkimus (ei lataa kuvia)
rad-loader query VAR9946804

# 3. Lataa yksittäinen tutkimus
rad-loader load projektini VAR9946804

# 4. Lataa useita kerralla
rad-loader load projektini VAR9946804 VAR9946805 VAR9946806

# 5. Lataa tiedostosta (yksi accession per rivi)
rad-loader load projektini --file accession_lista.txt

# 6. Kuivaharjoittelu (näyttää mitä ladattaisiin, ei lataa)
rad-loader load projektini --file accession_lista.txt --dry-run

# 7. Tarkista projektin tila (sis. poikkeamien tunnistus)
rad-loader status projektini

# 8. Tarkista auditointiloki
rad-loader audit projektini
rad-loader audit --all
```

Lisää `--human` ennen komentoa luettavampaa tulostetta varten:

```bash
rad-loader --human echo
rad-loader --human query VAR9946804
rad-loader --human status projektini
```

## Tulos

Kuvat tallentuvat konfiguraatiossa määritettyyn hakemistoon:

```
<output_base_dir>/
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
```

- Jokainen tutkimus saa juoksevan tunnisteen (`case0001`, `case0002`, ...)
- `key.csv` yhdistää tunnisteen accession-numeroon, modaliteettiin ja päivämäärään
- Jo ladatut tutkimukset ohitetaan automaattisesti (voi ajaa uudestaan turvallisesti)

## Accession-listan formaatti

Tekstitiedosto, yksi accession per rivi. Tyhjät rivit ja `#`-kommentit sallitaan:

```
# Aivoverenvuoto-tutkimus, kevät 2026
VAR9946804
VAR9946805

# Kontrollipotilaat
VAR9946810
VAR9946811
```

## Verifiointi

### Latauksen verifiointi

Jokainen `load`-komento palauttaa `verification`-kentän:

- `not_found`: accession-numeroa ei löydy PACS:sta (kirjoitusvirhe?)
- `failed`: PACS-virhe (yritä uudelleen)
- `warnings`: epätavallinen kuvamäärä (< 5 tai > 5000)

### Projektin poikkeamien tunnistus

`status`-komento vertaa projektin tapauksia toisiinsa:
- Tapaukset joissa huomattavasti vähemmän sarjoja — mahdollisesti epätäydellinen tutkimus
- Tapaukset joissa paljon enemmän/vähemmän kuvia — tarkista
- Modaliteettipoikkeamat — väärä tutkimus?

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
| Kuvausparametrit (MR) | RepetitionTime, EchoTime, FlipAngle, MagneticFieldStrength, SliceThickness, DiffusionBValue, ... |
| Kuvausparametrit (CT) | KVP, ExposureTime, XRayTubeCurrent, ConvolutionKernel, ... |
| Kuvausparametrit (yleiset) | ProtocolName, BodyPartExamined, ContrastBolusAgent, PatientPosition |
| Pikselitiedot | Rows, Columns, PixelSpacing, BitsAllocated, WindowCenter/Width, RescaleSlope/Intercept |
| Sijainti/geometria | ImagePositionPatient, ImageOrientationPatient, SliceLocation, FrameOfReferenceUID |
| Laitteisto | Manufacturer, ManufacturerModelName, SoftwareVersions, DeviceSerialNumber |
| Pikselidata | PixelData (varsinainen kuva) |

### Rajoitukset

- **Burned-in annotations**: Kuviin poltetut tekstit (esim. potilaan nimi röntgenkuvassa) EI poistu. Tarkista kuvat manuaalisesti.
- **Structured Reports**: SR-objekteja ei anonymisoida — ne ohitetaan.
- **Yksisäikeinen**: Tutkimukset ladataan yksi kerrallaan (C-MOVE).

## Lisenssi

[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)
