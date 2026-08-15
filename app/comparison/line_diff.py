"""Line-level alignment between two documents.

This module answers "which lines correspond to which" using
`difflib.SequenceMatcher` over normalized line content, then reports
results in terms of the ORIGINAL (un-normalized) line text and original
1-based line numbers — normalization only ever affects what counts as
"equal", never what is displayed.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import zip_longest
from typing import List, Optional

from app.comparison.normalization import apply_settings_to_line
from app.core.models import ComparisonSettings


@dataclass(frozen=True)
class _LineRecord:
    line_no: int  # 1-based, original numbering
    raw_text: str
    norm_text: str


def _build_records(text: str, settings: ComparisonSettings) -> List[_LineRecord]:
    raw_lines = text.splitlines()
    records = []
    for idx, raw in enumerate(raw_lines, start=1):
        norm = apply_settings_to_line(raw, settings)
        if settings.ignore_blank_lines and norm.strip() == "":
            continue
        records.append(_LineRecord(idx, raw, norm))
    return records


@dataclass(frozen=True)
class AlignedLine:
    """One row of the aligned output: either side may be absent (None)."""

    a: Optional[_LineRecord]
    b: Optional[_LineRecord]
    is_equal: bool


def align_lines(
    text_a: str, text_b: str, settings: ComparisonSettings
) -> List[AlignedLine]:
    records_a = _build_records(text_a, settings)
    records_b = _build_records(text_b, settings)

    norm_a = [r.norm_text for r in records_a]
    norm_b = [r.norm_text for r in records_b]

    matcher = SequenceMatcher(None, norm_a, norm_b, autojunk=False)
    aligned: List[AlignedLine] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for a_rec, b_rec in zip(records_a[i1:i2], records_b[j1:j2]):
                aligned.append(AlignedLine(a_rec, b_rec, True))
        elif tag == "delete":
            for a_rec in records_a[i1:i2]:
                aligned.append(AlignedLine(a_rec, None, False))
        elif tag == "insert":
            for b_rec in records_b[j1:j2]:
                aligned.append(AlignedLine(None, b_rec, False))
        elif tag == "replace":
            a_slice = records_a[i1:i2]
            b_slice = records_b[j1:j2]
            for a_rec, b_rec in zip_longest(a_slice, b_slice, fillvalue=None):
                aligned.append(AlignedLine(a_rec, b_rec, False))

    return aligned
