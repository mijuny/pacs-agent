"""Temporary C-STORE SCP for receiving images from PACS.

Starts a DICOM SCP that accepts incoming C-STORE requests,
immediately anonymizes received files, and saves them to
the project output directory.
"""

from __future__ import annotations

import logging
import threading
import warnings
from pathlib import Path

from pydicom import Dataset
from pydicom.config import IGNORE
from pynetdicom import AE, evt
from pynetdicom.presentation import AllStoragePresentationContexts

from .anonymize import anonymize_dataset
from .config import Config

log = logging.getLogger(__name__)


class TemporarySCP:
    """A C-STORE SCP that receives, anonymizes, and saves DICOM files.

    Usage:
        scp = TemporarySCP(config, project_dir, case_id)
        scp.start()
        # ... trigger C-MOVE from PACS ...
        scp.stop()
        print(scp.received_files)
    """

    def __init__(
        self,
        config: Config,
        project_dir: Path,
        case_id: str,
    ) -> None:
        self.config = config
        self.project_dir = project_dir
        self.case_id = case_id
        self._server: AE | None = None
        self._thread: threading.Thread | None = None
        self._server_instance = None

        # Track received files: {SeriesInstanceUID: [file_paths]}
        self.received_files: dict[str, list[Path]] = {}
        self._series_counter: dict[str, int] = {}
        self._instance_counter: dict[str, int] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the SCP in a background thread."""
        ae = AE(ae_title=self.config.scp.ae_title)
        ae.supported_contexts = AllStoragePresentationContexts

        handlers = [(evt.EVT_C_STORE, self._handle_store)]

        self._server_instance = ae.start_server(
            ("0.0.0.0", self.config.scp.port),
            block=False,
            evt_handlers=handlers,
        )
        log.info(
            "SCP started on port %d (AE: %s)",
            self.config.scp.port,
            self.config.scp.ae_title,
        )

    def stop(self) -> None:
        """Stop the SCP."""
        if self._server_instance:
            self._server_instance.shutdown()
            self._server_instance = None
            log.info("SCP stopped")

    def _handle_store(self, event: evt.Event) -> int:
        """Handle incoming C-STORE request."""
        # Suppress pydicom validation warnings for non-standard VR values
        # from PACS (e.g. Philips sorting metadata in UI VR fields).
        # The data is preserved as-is; we just skip the validation noise.
        import pydicom.config as pydicom_config
        prev = pydicom_config.settings.reading_validation_mode
        pydicom_config.settings.reading_validation_mode = IGNORE
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                return self._process_store(event)
        finally:
            pydicom_config.settings.reading_validation_mode = prev

    def _process_store(self, event: evt.Event) -> int:
        ds: Dataset = event.dataset
        ds.file_meta = event.file_meta

        series_uid = getattr(ds, "SeriesInstanceUID", "unknown")

        with self._lock:
            if series_uid not in self._series_counter:
                self._series_counter[series_uid] = len(self._series_counter) + 1
            series_num = self._series_counter[series_uid]

            if series_uid not in self._instance_counter:
                self._instance_counter[series_uid] = 0
            self._instance_counter[series_uid] += 1
            inst_num = self._instance_counter[series_uid]

        anonymize_dataset(ds, self.case_id)

        series_dir = self.project_dir / self.case_id / f"series{series_num:02d}"
        series_dir.mkdir(parents=True, exist_ok=True)
        file_path = series_dir / f"{inst_num:05d}.dcm"
        ds.save_as(file_path, enforce_file_format=True)

        with self._lock:
            if series_uid not in self.received_files:
                self.received_files[series_uid] = []
            self.received_files[series_uid].append(file_path)

        log.debug("Stored: %s", file_path)
        return 0x0000  # success
