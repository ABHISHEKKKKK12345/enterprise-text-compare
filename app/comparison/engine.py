"""The comparison engine.

This is the heart of the application and is intentionally free of any Qt
or GUI dependency — it can be imported and used from a plain Python
script or a unit test with no display server available:

    from app.comparison.engine import ComparisonEngine
    result = ComparisonEngine().compare(source_a, source_b, settings)

Long-running comparisons (large files) support cooperative cancellation
via an optional `is_cancelled` callable and progress reporting via an
optional `on_progress` callable, so the GUI worker thread can drive both
without the engine knowing anything about threads or Qt signals.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Callable, List, Optional

from app.comparison import char_diff, word_diff
from app.comparison.line_diff import align_lines
from app.comparison.statistics import compute_statistics
from app.core.enums import ComparisonMode, DifferenceType
from app.core.exceptions import ComparisonCancelledError, ComparisonEngineError
from app.core.models import (
    ComparisonRequest,
    ComparisonResult,
    ComparisonSettings,
    Difference,
    SourceDocument,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int], None]
CancelledCheck = Callable[[], bool]

# Report progress at most this often (in number of aligned rows) to avoid
# flooding the GUI thread with signal emissions on huge files.
_PROGRESS_REPORT_STRIDE = 200


class ComparisonEngine:
    """Stateless, reusable engine. Safe to share a single instance."""

    def compare(
        self,
        source_a: SourceDocument,
        source_b: SourceDocument,
        settings: ComparisonSettings,
        *,
        on_progress: Optional[ProgressCallback] = None,
        is_cancelled: Optional[CancelledCheck] = None,
    ) -> ComparisonResult:
        start = time.monotonic()
        request = ComparisonRequest(source_a=source_a, source_b=source_b, settings=settings)

        if is_cancelled is not None and is_cancelled():
            raise ComparisonCancelledError("The comparison was cancelled.")

        try:
            aligned = align_lines(source_a.text, source_b.text, settings)
        except Exception as exc:  # noqa: BLE001
            raise ComparisonEngineError(
                "An error occurred while comparing the selected sources.",
                cause=exc,
            ) from exc

        differences: List[Difference] = []
        total_rows = len(aligned)

        for idx, row in enumerate(aligned):
            if is_cancelled is not None and idx % _PROGRESS_REPORT_STRIDE == 0:
                if is_cancelled():
                    raise ComparisonCancelledError("The comparison was cancelled.")

            if on_progress is not None and (
                idx % _PROGRESS_REPORT_STRIDE == 0 or idx == total_rows - 1
            ):
                percent = int(((idx + 1) / total_rows) * 100) if total_rows else 100
                on_progress(percent)

            change_type = DifferenceType.UNCHANGED if row.is_equal else (
                DifferenceType.MODIFIED
                if row.a is not None and row.b is not None
                else (DifferenceType.REMOVED if row.a is not None else DifferenceType.ADDED)
            )

            a_text = row.a.raw_text if row.a is not None else ""
            b_text = row.b.raw_text if row.b is not None else ""
            a_line_no = row.a.line_no if row.a is not None else None
            b_line_no = row.b.line_no if row.b is not None else None

            a_inline: List = []
            b_inline: List = []

            if change_type == DifferenceType.MODIFIED and settings.mode in (
                ComparisonMode.WORD,
                ComparisonMode.CHARACTER,
            ):
                if settings.mode == ComparisonMode.WORD:
                    a_inline, b_inline = word_diff.compute_inline_word_diff(a_text, b_text)
                else:
                    a_inline, b_inline = char_diff.diff_characters(a_text, b_text)

            differences.append(
                Difference(
                    index=idx,
                    change_type=change_type,
                    a_line_no=a_line_no,
                    b_line_no=b_line_no,
                    a_text=a_text,
                    b_text=b_text,
                    a_inline=a_inline,
                    b_inline=b_inline,
                )
            )

        statistics = compute_statistics(differences)
        duration = time.monotonic() - start

        logger.info(
            "Comparison complete: mode=%s lines=%d added=%d removed=%d modified=%d "
            "unchanged=%d duration=%.3fs",
            settings.mode.value,
            statistics.lines_compared,
            statistics.added,
            statistics.removed,
            statistics.modified,
            statistics.unchanged,
            duration,
        )

        return ComparisonResult(
            request=request,
            differences=differences,
            statistics=statistics,
            generated_at=datetime.now(),
            duration_seconds=duration,
        )
