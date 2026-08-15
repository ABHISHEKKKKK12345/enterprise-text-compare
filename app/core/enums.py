"""Enumerations shared across the application.

Keeping enums centralized avoids "magic strings" being scattered through the
codebase and gives type-checkers/IDEs something concrete to validate against.
"""
from __future__ import annotations

from enum import Enum, auto


class ComparisonMode(str, Enum):
    """The granularity at which two sources are compared."""

    LINE = "line"
    WORD = "word"
    CHARACTER = "character"

    @property
    def display_name(self) -> str:
        return {
            ComparisonMode.LINE: "Line Comparison",
            ComparisonMode.WORD: "Word Comparison",
            ComparisonMode.CHARACTER: "Character Comparison",
        }[self]


class DifferenceType(str, Enum):
    """Classification of a single diff segment/line."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class EncodingConfidence(str, Enum):
    """How confident the encoding detector is about a result."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FALLBACK = "fallback"


class LineEnding(str, Enum):
    CRLF = "crlf"
    LF = "lf"
    CR = "cr"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class Theme(str, Enum):
    LIGHT = "light"
    DARK = "dark"


class ExportFormat(str, Enum):
    HTML = "html"
    TXT = "txt"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"


class SourceOrigin(str, Enum):
    """Where a comparison source's text came from."""

    PASTED_TEXT = "pasted_text"
    FILE = "file"


class LogLevel(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class OperationStatus(Enum):
    """Status of a long-running (worker-thread) operation."""

    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    FAILED = auto()
