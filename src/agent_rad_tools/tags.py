"""PHI and KEEP tag definitions — the core of PID safety.

Allowlist approach: only tags in KEEP_TAGS survive anonymization.
Everything else is deleted. Private tags (odd group numbers) are
always deleted.
"""

from pydicom.tag import Tag

# ── Tags to explicitly DELETE (PHI) ──────────────────────────────

PHI_TAGS: set[Tag] = {
    # Patient identification
    Tag(0x0010, 0x0010),  # PatientName
    Tag(0x0010, 0x0020),  # PatientID
    Tag(0x0010, 0x0030),  # PatientBirthDate
    Tag(0x0010, 0x1000),  # OtherPatientIDs
    Tag(0x0010, 0x1001),  # OtherPatientNames
    Tag(0x0010, 0x0021),  # IssuerOfPatientID
    Tag(0x0010, 0x1040),  # PatientAddress
    Tag(0x0010, 0x2154),  # PatientTelephoneNumbers
    Tag(0x0010, 0x21B0),  # AdditionalPatientHistory
    Tag(0x0010, 0x4000),  # PatientComments
    # Physician / operator identification
    Tag(0x0008, 0x0090),  # ReferringPhysicianName
    Tag(0x0008, 0x1050),  # PerformingPhysicianName
    Tag(0x0008, 0x1070),  # OperatorsName
    Tag(0x0032, 0x1032),  # RequestingPhysician
    # Institution
    Tag(0x0008, 0x0080),  # InstitutionName
    Tag(0x0008, 0x0081),  # InstitutionAddress
    # Sequences that may contain PHI
    Tag(0x0040, 0x0275),  # RequestAttributesSequence
}


# ── Tags to KEEP (allowlist) ─────────────────────────────────────
# Only these tags (plus PixelData) survive. Grouped by function.

KEEP_TAGS: set[Tag] = {
    # ── Identifiers (non-patient) ──
    Tag(0x0008, 0x0050),  # AccessionNumber
    Tag(0x0020, 0x000D),  # StudyInstanceUID
    Tag(0x0020, 0x000E),  # SeriesInstanceUID
    Tag(0x0008, 0x0018),  # SOPInstanceUID
    Tag(0x0008, 0x0016),  # SOPClassUID
    Tag(0x0020, 0x0052),  # FrameOfReferenceUID
    # NOTE: StudyID (0020,0010) deliberately excluded — can mirror PatientID

    # ── Study/Series metadata ──
    Tag(0x0008, 0x0005),  # SpecificCharacterSet
    Tag(0x0008, 0x0008),  # ImageType
    Tag(0x0008, 0x0020),  # StudyDate
    Tag(0x0008, 0x0021),  # SeriesDate
    Tag(0x0008, 0x0030),  # StudyTime
    Tag(0x0008, 0x0031),  # SeriesTime
    Tag(0x0008, 0x0060),  # Modality
    Tag(0x0008, 0x0061),  # ModalitiesInStudy
    Tag(0x0008, 0x1030),  # StudyDescription
    Tag(0x0008, 0x103E),  # SeriesDescription
    Tag(0x0020, 0x0011),  # SeriesNumber
    Tag(0x0020, 0x0013),  # InstanceNumber
    Tag(0x0008, 0x0070),  # Manufacturer
    Tag(0x0008, 0x1090),  # ManufacturerModelName
    Tag(0x0018, 0x1020),  # SoftwareVersions
    Tag(0x0020, 0x4000),  # ImageComments  # study-level, rarely PHI

    # ── Patient demographics (non-identifying alone) ──
    Tag(0x0010, 0x0040),  # PatientSex
    Tag(0x0010, 0x1010),  # PatientAge
    Tag(0x0010, 0x1020),  # PatientSize
    Tag(0x0010, 0x1030),  # PatientWeight

    # ── Acquisition parameters (group 0x0018) ──
    Tag(0x0018, 0x0010),  # ContrastBolusAgent
    Tag(0x0018, 0x0015),  # BodyPartExamined
    Tag(0x0018, 0x0020),  # ScanningSequence
    Tag(0x0018, 0x0021),  # SequenceVariant
    Tag(0x0018, 0x0022),  # ScanOptions
    Tag(0x0018, 0x0023),  # MRAcquisitionType
    Tag(0x0018, 0x0024),  # SequenceName
    Tag(0x0018, 0x0050),  # SliceThickness
    Tag(0x0018, 0x0060),  # KVP
    Tag(0x0018, 0x0080),  # RepetitionTime
    Tag(0x0018, 0x0081),  # EchoTime
    Tag(0x0018, 0x0082),  # InversionTime
    Tag(0x0018, 0x0083),  # NumberOfAverages
    Tag(0x0018, 0x0084),  # ImagingFrequency
    Tag(0x0018, 0x0085),  # ImagedNucleus
    Tag(0x0018, 0x0086),  # EchoNumbers
    Tag(0x0018, 0x0087),  # MagneticFieldStrength
    Tag(0x0018, 0x0088),  # SpacingBetweenSlices
    Tag(0x0018, 0x0090),  # DataCollectionDiameter
    Tag(0x0018, 0x0091),  # EchoTrainLength
    Tag(0x0018, 0x0093),  # PercentSampling
    Tag(0x0018, 0x0094),  # PercentPhaseFieldOfView
    Tag(0x0018, 0x0095),  # PixelBandwidth
    Tag(0x0018, 0x1000),  # DeviceSerialNumber
    Tag(0x0018, 0x1030),  # ProtocolName
    Tag(0x0018, 0x1040),  # ContrastBolusRoute
    Tag(0x0018, 0x1050),  # SpatialResolution
    Tag(0x0018, 0x1060),  # TriggerTime
    Tag(0x0018, 0x1100),  # ReconstructionDiameter
    Tag(0x0018, 0x1110),  # DistanceSourceToDetector
    Tag(0x0018, 0x1111),  # DistanceSourceToPatient
    Tag(0x0018, 0x1120),  # GantryDetectorTilt
    Tag(0x0018, 0x1130),  # TableHeight
    Tag(0x0018, 0x1140),  # RotationDirection
    Tag(0x0018, 0x1150),  # ExposureTime
    Tag(0x0018, 0x1151),  # XRayTubeCurrent
    Tag(0x0018, 0x1152),  # Exposure
    Tag(0x0018, 0x1153),  # ExposureInuAs
    Tag(0x0018, 0x1160),  # FilterType
    Tag(0x0018, 0x1170),  # GeneratorPower
    Tag(0x0018, 0x1190),  # FocalSpots
    Tag(0x0018, 0x1200),  # DateOfLastCalibration
    Tag(0x0018, 0x1201),  # TimeOfLastCalibration
    Tag(0x0018, 0x1210),  # ConvolutionKernel
    Tag(0x0018, 0x1250),  # ReceiveCoilName
    Tag(0x0018, 0x1251),  # TransmitCoilName
    Tag(0x0018, 0x1310),  # AcquisitionMatrix
    Tag(0x0018, 0x1312),  # InPlanePhaseEncodingDirection
    Tag(0x0018, 0x1314),  # FlipAngle
    Tag(0x0018, 0x1316),  # SAR
    Tag(0x0018, 0x5100),  # PatientPosition
    Tag(0x0018, 0x9073),  # AcquisitionDuration
    Tag(0x0018, 0x9087),  # DiffusionBValue
    Tag(0x0018, 0x9089),  # DiffusionGradientOrientation

    # ── Pixel description (group 0x0028) ──
    Tag(0x0028, 0x0002),  # SamplesPerPixel
    Tag(0x0028, 0x0004),  # PhotometricInterpretation
    Tag(0x0028, 0x0006),  # PlanarConfiguration
    Tag(0x0028, 0x0008),  # NumberOfFrames
    Tag(0x0028, 0x0010),  # Rows
    Tag(0x0028, 0x0011),  # Columns
    Tag(0x0028, 0x0030),  # PixelSpacing
    Tag(0x0028, 0x0100),  # BitsAllocated
    Tag(0x0028, 0x0101),  # BitsStored
    Tag(0x0028, 0x0102),  # HighBit
    Tag(0x0028, 0x0103),  # PixelRepresentation
    Tag(0x0028, 0x0120),  # PixelPaddingValue
    Tag(0x0028, 0x1050),  # WindowCenter
    Tag(0x0028, 0x1051),  # WindowWidth
    Tag(0x0028, 0x1052),  # RescaleIntercept
    Tag(0x0028, 0x1053),  # RescaleSlope
    Tag(0x0028, 0x1054),  # RescaleType
    Tag(0x0028, 0x1055),  # WindowCenterWidthExplanation
    Tag(0x0028, 0x2110),  # LossyImageCompression
    Tag(0x0028, 0x2112),  # LossyImageCompressionRatio

    # ── Spatial / positioning ──
    Tag(0x0020, 0x0032),  # ImagePositionPatient
    Tag(0x0020, 0x0037),  # ImageOrientationPatient
    Tag(0x0020, 0x1041),  # SliceLocation
    Tag(0x0018, 0x0050),  # SliceThickness (also in acquisition)
    Tag(0x0028, 0x0030),  # PixelSpacing (also in pixel description)

    # ── Pixel data ──
    Tag(0x7FE0, 0x0010),  # PixelData

    # ── Transfer syntax / file meta ──
    Tag(0x0002, 0x0000),  # FileMetaInformationGroupLength
    Tag(0x0002, 0x0001),  # FileMetaInformationVersion
    Tag(0x0002, 0x0002),  # MediaStorageSOPClassUID
    Tag(0x0002, 0x0003),  # MediaStorageSOPInstanceUID
    Tag(0x0002, 0x0010),  # TransferSyntaxUID
    Tag(0x0002, 0x0012),  # ImplementationClassUID
    Tag(0x0002, 0x0013),  # ImplementationVersionName

    # ── Count tags (C-FIND responses) ──
    Tag(0x0020, 0x1206),  # NumberOfSeriesRelatedInstances
    Tag(0x0020, 0x1208),  # NumberOfStudyRelatedInstances
    Tag(0x0020, 0x1209),  # NumberOfStudyRelatedSeries  (non-standard but common)
}


def is_private_tag(tag: Tag) -> bool:
    """Private tags have odd group numbers."""
    return tag.group % 2 != 0
