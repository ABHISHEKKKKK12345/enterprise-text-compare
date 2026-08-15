"""Typed data models.

Using dataclasses throughout avoids passing loosely-structured dicts
between layers, gives static type-checking, and makes the comparison
engine's public contract explicit and testable independent of the GUI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.core.enums import (
    ComparisonMode,
    DifferenceType,
    EncodingConfidence,
    ExportFormat,
    LineEnding,
    SourceOrigin,
    Theme,
)


@dataclass(frozen=True)
class FileMetadata:
    """Metadata about a file that was loaded as a comparison source."""

    path: Path
    size_bytes: int
    encoding: str
    encoding_confidence: EncodingConfidence
    line_ending: LineEnding
    modified_at: Optional[datetime] = None


@dataclass(frozen=True)
class SourceDocument:
    """One side of a comparison (Source A or Source B)."""

    label: str
    text: str
    origin: SourceOrigin
    file_metadata: Optional[FileMetadata] = None

    @property
    def is_empty(self) -> bool:
        return len(self.text) == 0

    @property
    def line_count(self) -> int:
        if self.is_empty:
            return 0
        return len(self.text.splitlines())


@dataclass(frozen=True)
class ComparisonSettings:
    """All user-configurable options that affect comparison output.

    Immutable by design: a `ComparisonResult` should always be
    reproducible from its originating `ComparisonSettings` and the two
    `SourceDocument`s, which makes results easy to reason about and test.
    """

    mode: ComparisonMode = ComparisonMode.LINE
    case_sensitive: bool = True
    ignore_leading_trailing_whitespace: bool = False
    ignore_repeated_spaces: bool = False
    ignore_blank_lines: bool = False
    ignore_line_ending_differences: bool = True
    normalize_unicode: bool = False
    context_lines: int = 3

    def normalized_copy_note(self) -> str:
        """Human-readable summary used in export reports / status bar."""
        parts = [self.mode.display_name]
        if not self.case_sensitive:
            parts.append("case-insensitive")
        if self.ignore_leading_trailing_whitespace:
            parts.append("trim whitespace")
        if self.ignore_repeated_spaces:
            parts.append("collapse spaces")
        if self.ignore_blank_lines:
            parts.append("ignore blank lines")
        if self.ignore_line_ending_differences:
            parts.append("ignore line endings")
        if self.normalize_unicode:
            parts.append("Unicode NFC")
        return ", ".join(parts)


@dataclass(frozen=True)
class InlineChange:
    """A sub-line (word/character) change span, used for fine-grained highlighting."""

    text: str
    change_type: DifferenceType


@dataclass(frozen=True)
class Difference:
    """A single unit of difference between the two sources.

    For LINE mode this represents one changed line (or block); the
    `a_line_no` / `b_line_no` fields are 1-based line numbers, or ``None``
    when a side has no corresponding line (pure add/remove).
    """

    index: int
    change_type: DifferenceType
    a_line_no: Optional[int]
    b_line_no: Optional[int]
    a_text: str
    b_text: str
    a_inline: List[InlineChange] = field(default_factory=list)
    b_inline: List[InlineChange] = field(default_factory=list)


@dataclass(frozen=True)
class DifferenceStatistics:
    lines_compared: int
    added: int
    removed: int
    modified: int
    unchanged: int

    @property
    def total_differences(self) -> int:
        return self.added + self.removed + self.modified

    @property
    def is_identical(self) -> bool:
        return self.total_differences == 0


@dataclass(frozen=True)
class ComparisonRequest:
    source_a: SourceDocument
    source_b: SourceDocument
    settings: ComparisonSettings


@dataclass(frozen=True)
class ComparisonResult:
    request: ComparisonRequest
    differences: List[Difference]
    statistics: DifferenceStatistics
    generated_at: datetime
    duration_seconds: float


@dataclass
class ApplicationSettings:
    """Persisted, user-editable application preferences."""

    theme: Theme = Theme.LIGHT
    font_family: str = "Consolas, 'DejaVu Sans Mono', 'Courier New', monospace"
    font_size: int = 10
    default_export_format: ExportFormat = ExportFormat.HTML
    worker_thread_count: int = 2
    large_file_threshold_bytes: int = 10 * 1024 * 1024
    log_level: str = "INFO"
    comparison_settings: ComparisonSettings = field(default_factory=ComparisonSettings)


@dataclass(frozen=True)
class ErrorInformation:
    """Structured error info surfaced to the GUI's error dialog."""

    error_id: str
    code: str
    user_message: str
    technical_detail: str
    occurred_at: datetime
    log_reference: Optional[Path] = None
