"""ComparisonService — the orchestration layer between GUI/workers and the
domain (comparison engine, file I/O). Contains no Qt imports so it can be
unit- and integration-tested headlessly.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from app.comparison.engine import ComparisonEngine
from app.core.enums import SourceOrigin
from app.core.exceptions import InvalidComparisonInputError
from app.core.models import ComparisonResult, ComparisonSettings, SourceDocument
from app.io.file_reader import ReadResult, read_text_file

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int], None]
CancelledCheck = Callable[[], bool]


class ComparisonService:
    """Stateless facade used by the GUI (directly or via a worker thread)."""

    def __init__(self, engine: Optional[ComparisonEngine] = None) -> None:
        self._engine = engine or ComparisonEngine()

    def load_source_from_file(
        self,
        path: Path,
        label: str,
        *,
        force_encoding: Optional[str] = None,
        huge_file_confirmed: bool = False,
        huge_file_threshold: int,
    ) -> SourceDocument:
        result: ReadResult = read_text_file(
            path,
            force_encoding=force_encoding,
            huge_file_confirmed=huge_file_confirmed,
            huge_file_threshold=huge_file_threshold,
        )
        return SourceDocument(
            label=label,
            text=result.text,
            origin=SourceOrigin.FILE,
            file_metadata=result.metadata,
        )

    def load_source_from_text(self, text: str, label: str) -> SourceDocument:
        return SourceDocument(label=label, text=text, origin=SourceOrigin.PASTED_TEXT)

    def compare(
        self,
        source_a: SourceDocument,
        source_b: SourceDocument,
        settings: ComparisonSettings,
        *,
        on_progress: Optional[ProgressCallback] = None,
        is_cancelled: Optional[CancelledCheck] = None,
    ) -> ComparisonResult:
        if source_a is None or source_b is None:
            raise InvalidComparisonInputError(
                "Select two files or enter text in both panels before comparing."
            )
        logger.info(
            "Starting comparison: a_label=%s b_label=%s a_lines=%d b_lines=%d mode=%s",
            source_a.label,
            source_b.label,
            source_a.line_count,
            source_b.line_count,
            settings.mode.value,
        )
        return self._engine.compare(
            source_a, source_b, settings, on_progress=on_progress, is_cancelled=is_cancelled
        )
