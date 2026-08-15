"""Safe file writing: atomic writes and secure temporary file handling.

Writes go to a temporary file in the destination directory first, then
are atomically renamed into place, so a crash or power loss mid-write
never leaves a truncated/corrupted destination file. Original source
files passed into the comparison engine are NEVER modified by this
module — it is only used for explicit "Save" / "Export" actions on
content the user chose to write out.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from app.core.exceptions import ExportError, PermissionDeniedError

logger = logging.getLogger(__name__)


def write_text_atomic(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    directory = path.parent
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ExportError(
            f"Unable to create the destination folder for '{path.name}'.", cause=exc
        ) from exc

    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(directory))
    tmp_path = Path(tmp_name)
    try:
        with open(fd, "w", encoding=encoding, newline="") as handle:
            handle.write(content)
        tmp_path.replace(path)
        logger.info("Wrote file: %s (%d chars)", path.name, len(content))
    except PermissionError as exc:
        _cleanup(tmp_path)
        raise PermissionDeniedError(
            f"Permission denied while writing '{path.name}'.", cause=exc
        ) from exc
    except OSError as exc:
        _cleanup(tmp_path)
        raise ExportError(f"Unable to write '{path.name}'.", cause=exc) from exc


def _cleanup(tmp_path: Path) -> None:
    try:
        if tmp_path.exists():
            tmp_path.unlink()
    except OSError:
        logger.warning("Failed to clean up temporary file: %s", tmp_path, exc_info=True)
