"""Character encoding detection.

Strategy:
1. Check for a byte-order mark (BOM) — cheap and 100% reliable when present.
2. Try `charset_normalizer` if it is installed (optional dependency,
   provides much better detection than heuristics alone for ambiguous
   8-bit encodings). The import is optional and the app works without it.
3. Fall back to attempting a fixed, ordered list of common encodings
   (utf-8, utf-8-sig, utf-16, cp1252, latin-1), accepting the first one
   that decodes without error.
4. `latin-1` never fails to decode (it maps every byte 0-255), so it is
   always available as an absolute last resort — the detector therefore
   never raises for "cannot determine encoding" on a non-empty file; it
   degrades confidence instead of failing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.constants import FALLBACK_ENCODINGS
from app.core.enums import EncodingConfidence

logger = logging.getLogger(__name__)

try:
    from charset_normalizer import from_bytes as _cn_from_bytes

    _HAS_CHARSET_NORMALIZER = True
except ImportError:  # optional dependency
    _HAS_CHARSET_NORMALIZER = False

_BOMS = [
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe\x00\x00", "utf-32"),
    (b"\x00\x00\xfe\xff", "utf-32"),
    (b"\xff\xfe", "utf-16"),
    (b"\xfe\xff", "utf-16"),
]


@dataclass(frozen=True)
class DetectionResult:
    encoding: str
    confidence: EncodingConfidence


def detect_encoding(data: bytes) -> DetectionResult:
    if not data:
        return DetectionResult("utf-8", EncodingConfidence.HIGH)

    for bom_bytes, encoding in _BOMS:
        if data.startswith(bom_bytes):
            return DetectionResult(encoding, EncodingConfidence.HIGH)

    if _HAS_CHARSET_NORMALIZER:
        try:
            best = _cn_from_bytes(data).best()
            if best is not None and best.encoding:
                return DetectionResult(best.encoding, EncodingConfidence.HIGH)
        except Exception:  # noqa: BLE001 - detector failure must not crash
            logger.debug("charset_normalizer detection failed; using fallback chain.")

    for candidate in FALLBACK_ENCODINGS:
        try:
            data.decode(candidate)
            confidence = (
                EncodingConfidence.MEDIUM if candidate == "utf-8" else EncodingConfidence.LOW
            )
            return DetectionResult(candidate, confidence)
        except (UnicodeDecodeError, LookupError):
            continue

    # latin-1 is a total mapping; this line is effectively unreachable but
    # kept as an explicit, documented last resort.
    return DetectionResult("latin-1", EncodingConfidence.FALLBACK)


def decode_with_detection(data: bytes) -> tuple[str, DetectionResult]:
    result = detect_encoding(data)
    try:
        text = data.decode(result.encoding)
    except (UnicodeDecodeError, LookupError):
        text = data.decode("latin-1", errors="replace")
        result = DetectionResult("latin-1", EncodingConfidence.FALLBACK)
    return text, result
