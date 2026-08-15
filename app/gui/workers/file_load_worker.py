"""Background file-load worker.

Loading a file involves disk I/O and encoding detection, both of which
can be slow enough on very large files to freeze a GUI thread.

Reusable, persistent-thread pattern: see the design note in
`comparison_worker.py` for why this worker is created once and dispatched
via a `start(...)` slot on an already-running QThread, rather than being
re-created (and its QThread re-created/torn down) for every file load.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from app.core.exceptions import ApplicationError
from app.services.comparison_service import ComparisonService
from app.utils.error_handler import build_error_information

logger = logging.getLogger(__name__)


class FileLoadWorker(QObject):
    """Long-lived worker, moved to a persistent background QThread.

    Call `start(path, label, force_encoding, huge_file_confirmed,
    huge_file_threshold)` (typically via a queued signal connection from
    the GUI thread) to load a file; it may be called repeatedly over the
    worker's lifetime.
    """

    result_ready = Signal(object)  # SourceDocument
    failed = Signal(object)  # ErrorInformation
    finished = Signal()

    def __init__(self, service: ComparisonService) -> None:
        super().__init__()
        self._service = service

    @Slot(object, str, object, bool, int)
    def start(
        self,
        path: Path,
        label: str,
        force_encoding: Optional[str],
        huge_file_confirmed: bool,
        huge_file_threshold: int,
    ) -> None:
        try:
            document = self._service.load_source_from_file(
                path,
                label,
                force_encoding=force_encoding,
                huge_file_confirmed=huge_file_confirmed,
                huge_file_threshold=huge_file_threshold,
            )
        except ApplicationError as exc:
            self.failed.emit(build_error_information(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(build_error_information(exc))
        else:
            self.result_ready.emit(document)
        finally:
            self.finished.emit()
