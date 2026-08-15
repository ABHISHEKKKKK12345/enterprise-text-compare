"""Reading text files for comparison.

Every failure mode described in the spec (missing file, permission
error, invalid path, unsupported binary format, huge file, corrupted /
undecodable bytes) is translated into a specific `ApplicationError`
subclass with a friendly `user_message`. Callers (the comparison service
/ GUI workers) never need to catch bare `OSError` or `UnicodeDecodeError`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.constants import (
    DEFAULT_HUGE_FILE_WARNING_BYTES,
    SUPPORTED_TEXT_EXTENSIONS,
)
from app.core.enums import LineEnding
from app.core.exceptions import (
    FileAccessError,
    FileNotFoundInAppError,
    FileTooLargeError,
    PermissionDeniedError,
    UnsupportedFileTypeError,
)
from app.core.models import FileMetadata
from app.io.encoding import decode_with_detection

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReadResult:
    text: str
    metadata: FileMetadata


def _detect_line_ending(text: str) -> LineEnding:
    has_crlf = "\r\n" in text
    stripped = text.replace("\r\n", "")
    has_lone_cr = "\r" in stripped
    has_lone_lf = "\n" in stripped

    kinds = sum([has_crlf, has_lone_cr, has_lone_lf])
    if kinds == 0:
        return LineEnding.UNKNOWN
    if kinds > 1:
        return LineEnding.MIXED
    if has_crlf:
        return LineEnding.CRLF
    if has_lone_cr:
        return LineEnding.CR
    return LineEnding.LF


def is_supported_text_file(path: Path, *, force: bool = False) -> bool:
    if force:
        return True
    return path.suffix.lower() in SUPPORTED_TEXT_EXTENSIONS or path.suffix == ""


_UTF16_32_BOMS = (b"\xff\xfe", b"\xfe\xff", b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")


def looks_binary(data: bytes) -> bool:
    """Heuristic: presence of NUL bytes strongly indicates binary content.

    UTF-16/UTF-32 encoded text is a legitimate exception: it contains NUL
    bytes by design (every other byte is 0x00 for ASCII characters), so
    files starting with a UTF-16/UTF-32 byte-order mark are never flagged
    as binary by this heuristic.
    """
    if data.startswith(_UTF16_32_BOMS):
        return False
    return b"\x00" in data[:8192]


def read_text_file(
    path: Path,
    *,
    force_encoding: Optional[str] = None,
    allow_unsupported_extension: bool = False,
    huge_file_confirmed: bool = False,
    huge_file_threshold: int = DEFAULT_HUGE_FILE_WARNING_BYTES,
) -> ReadResult:
    """Read `path` and return decoded text plus metadata.

    Raises a specific `ApplicationError` subclass for every anticipated
    failure mode; never raises a bare OSError/UnicodeDecodeError to callers.
    """
    if not path.exists():
        raise FileNotFoundInAppError(
            f"The file '{path.name}' could not be found. It may have been "
            "moved or deleted since it was selected.",
            technical_detail=f"Missing path: {path}",
        )

    if not path.is_file():
        raise FileAccessError(
            f"'{path.name}' is not a file that can be compared.",
            technical_detail=f"Not a regular file: {path}",
        )

    if not allow_unsupported_extension and not is_supported_text_file(path):
        raise UnsupportedFileTypeError(
            f"'{path.name}' has an unsupported file type for text comparison. "
            "Binary files cannot be compared as text.",
            technical_detail=f"Unsupported extension: {path.suffix}",
        )

    try:
        size_bytes = path.stat().st_size
        modified_at = datetime.fromtimestamp(path.stat().st_mtime)
    except PermissionError as exc:
        raise PermissionDeniedError(
            f"Permission denied while accessing '{path.name}'. Check that you "
            "have read access to this file.",
            cause=exc,
        ) from exc
    except OSError as exc:
        raise FileAccessError(
            f"Unable to access '{path.name}'.", cause=exc
        ) from exc

    if size_bytes >= huge_file_threshold and not huge_file_confirmed:
        raise FileTooLargeError(
            f"'{path.name}' is very large and may take a while to compare. "
            "Confirm to proceed anyway.",
            technical_detail=f"size={size_bytes} threshold={huge_file_threshold}",
        )

    try:
        data = path.read_bytes()
    except PermissionError as exc:
        raise PermissionDeniedError(
            f"Permission denied while reading '{path.name}'.", cause=exc
        ) from exc
    except FileNotFoundError as exc:
        raise FileNotFoundInAppError(
            f"'{path.name}' was deleted or moved while it was being read.", cause=exc
        ) from exc
    except OSError as exc:
        raise FileAccessError(f"Unable to read '{path.name}'.", cause=exc) from exc

    if not allow_unsupported_extension and looks_binary(data):
        raise UnsupportedFileTypeError(
            f"'{path.name}' appears to be a binary file and cannot be compared as text.",
            technical_detail="NUL byte detected in first 8KB.",
        )

    if force_encoding:
        try:
            text = data.decode(force_encoding)
            from app.io.encoding import DetectionResult
            from app.core.enums import EncodingConfidence

            detection = DetectionResult(force_encoding, EncodingConfidence.HIGH)
        except (UnicodeDecodeError, LookupError) as exc:
            raise FileAccessError(
                f"'{path.name}' could not be decoded using the selected encoding "
                f"('{force_encoding}'). Try a different encoding.",
                cause=exc,
            ) from exc
    else:
        text, detection = decode_with_detection(data)

    metadata = FileMetadata(
        path=path,
        size_bytes=size_bytes,
        encoding=detection.encoding,
        encoding_confidence=detection.confidence,
        line_ending=_detect_line_ending(text),
        modified_at=modified_at,
    )
    logger.info(
        "Read file: name=%s size=%d encoding=%s confidence=%s",
        path.name,
        size_bytes,
        detection.encoding,
        detection.confidence.value,
    )
    return ReadResult(text=text, metadata=metadata)
