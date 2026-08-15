"""Small, generic, dependency-free helper functions."""
from __future__ import annotations

from pathlib import Path


def human_readable_size(num_bytes: int) -> str:
    """Format a byte count as a human-readable string (e.g. '4.2 MB')."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB"


def safe_filename_stub(path: Path) -> str:
    """A filesystem/HTML-safe label derived from a path, for reports."""
    return path.name if path else "untitled"


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
