"""Background comparison worker.

Follows the standard "QObject worker + QThread + moveToThread" pattern
rather than subclassing QThread directly (subclassing is a well-known Qt
anti-pattern that mixes thread-affinity issues into business logic).
Cancellation is cooperative: `request_cancel()` sets a flag that the
comparison engine polls periodically (see `_PROGRESS_REPORT_STRIDE` in
`app/comparison/engine.py`), so the thread always exits cleanly instead
of being forcefully terminated.

DESIGN NOTE — reusable worker, persistent thread:
An earlier version of this worker was one-shot: a brand-new QThread and
ComparisonWorker were created, started, and torn down for every single
comparison. Under repeated rapid-fire comparisons this proved genuinely
racy — tearing down one QThread and immediately spinning up another can
intermittently leave the old QThread's native OS thread not fully joined
by the time it is deleteLater()'d, producing "QThread: Destroyed while
thread is still running" and, occasionally, a comparison that never
completes at all. This was reproduced and confirmed via a 20-run stress
test (see project history), not assumed.

The fix is the standard, more robust Qt pattern for a "repeated
background job" worker: the QThread and this worker are created ONCE and
kept alive for the application's lifetime (see MainWindow), and each new
comparison request is dispatched into the ALREADY-RUNNING thread via a
queued signal -> `start()` slot call, rather than by creating a new
thread. There is no thread creation/teardown between comparisons, so the
entire class of races above cannot occur.
"""
from __future__ import annotations

import logging
import threading

from PySide6.QtCore import QObject, Signal, Slot

from app.core.exceptions import ApplicationError, ComparisonCancelledError
from app.core.models import ComparisonSettings, SourceDocument
from app.services.comparison_service import ComparisonService
from app.utils.error_handler import build_error_information

logger = logging.getLogger(__name__)


class ComparisonWorker(QObject):
    """Long-lived worker, moved to a persistent background QThread.

    Call `start(source_a, source_b, settings)` (typically via a queued
    signal connection from the GUI thread) to run a comparison; it may be
    called repeatedly over the worker's lifetime. `finished` is emitted at
    the end of each individual comparison (not when the worker itself is
    destroyed) so the GUI can reset its per-comparison UI state each time.
    """

    started = Signal()
    progress = Signal(int)
    result_ready = Signal(object)  # ComparisonResult
    cancelled = Signal()
    failed = Signal(object)  # ErrorInformation
    finished = Signal()

    def __init__(self, service: ComparisonService) -> None:
        super().__init__()
        self._service = service
        self._cancel_event = threading.Event()

    def request_cancel(self) -> None:
        self._cancel_event.set()

    @Slot(object, object, object)
    def start(
        self,
        source_a: SourceDocument,
        source_b: SourceDocument,
        settings: ComparisonSettings,
    ) -> None:
        # Reset cancellation state at the start of each new job; a
        # cancel request from a *previous* job must never leak into the
        # next one.
        self._cancel_event.clear()
        self.started.emit()
        try:
            result = self._service.compare(
                source_a,
                source_b,
                settings,
                on_progress=self.progress.emit,
                is_cancelled=self._cancel_event.is_set,
            )
        except ComparisonCancelledError:
            logger.info("Comparison cancelled by user.")
            self.cancelled.emit()
        except ApplicationError as exc:
            info = build_error_information(exc)
            self.failed.emit(info)
        except Exception as exc:  # noqa: BLE001 - must not crash the worker thread
            info = build_error_information(exc)
            self.failed.emit(info)
        else:
            self.result_ready.emit(result)
        finally:
            self.finished.emit()
