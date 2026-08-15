"""Normalization applied (only when explicitly enabled) prior to diffing.

CRITICAL INVARIANT: normalization NEVER mutates the original
`SourceDocument.text`. It produces a separate, derived string used only
for the purpose of computing the diff. The GUI always displays the
original, untouched text; normalization only affects what is considered
"different".
"""
from __future__ import annotations

import re
import unicodedata

from app.core.models import ComparisonSettings

_REPEATED_SPACES_RE = re.compile(r"[ \t]{2,}")
_TRAILING_WS_RE = re.compile(r"[ \t]+$", re.MULTILINE)
_LEADING_WS_RE = re.compile(r"^[ \t]+", re.MULTILINE)


def normalize_line_endings(text: str) -> str:
    """Convert CRLF and lone CR to LF for comparison purposes only."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def apply_settings_to_line(line: str, settings: ComparisonSettings) -> str:
    """Apply the configured normalization rules to a single line."""
    result = line

    if settings.normalize_unicode:
        result = unicodedata.normalize("NFC", result)

    if settings.ignore_leading_trailing_whitespace:
        result = result.strip()

    if settings.ignore_repeated_spaces:
        result = _REPEATED_SPACES_RE.sub(" ", result)

    if not settings.case_sensitive:
        result = result.casefold()

    return result


def prepare_lines(text: str, settings: ComparisonSettings) -> list[str]:
    """Split text into lines and apply normalization for comparison.

    Line-ending normalization is applied before splitting whenever the
    setting is enabled (it must be, or `splitlines()` will produce
    spurious differences purely from CRLF vs LF). Blank-line filtering is
    handled by the caller (engine) since removing lines shifts indices
    and the engine needs to track original line numbers.
    """
    working = normalize_line_endings(text) if settings.ignore_line_ending_differences else text
    raw_lines = working.split("\n")
    # A trailing newline produces one spurious empty final element; drop it
    # only when the original text actually ended with a newline.
    if raw_lines and raw_lines[-1] == "" and working.endswith("\n"):
        raw_lines = raw_lines[:-1]
    return [apply_settings_to_line(line, settings) for line in raw_lines]
