"""Word-level and character-level inline diffing for a single changed line pair.

Uses `difflib.SequenceMatcher` on tokenized sequences (words, preserving
separators as their own tokens so whitespace differences remain visible;
or individual characters). This is intentionally kept as pure functions
with no GUI dependency so it is trivially unit-testable.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import List

from app.core.enums import DifferenceType
from app.core.models import InlineChange

_WORD_TOKEN_RE = re.compile(r"\w+|[^\w\s]|\s+", re.UNICODE)


def _tokenize_words(line: str) -> List[str]:
    """Split into words, punctuation runs, and whitespace runs as tokens."""
    return _WORD_TOKEN_RE.findall(line)


def compute_inline_word_diff(
    a_text: str, b_text: str
) -> tuple[List[InlineChange], List[InlineChange]]:
    a_tokens = _tokenize_words(a_text)
    b_tokens = _tokenize_words(b_text)
    return _diff_tokens(a_tokens, b_tokens)


def compute_inline_char_diff(
    a_text: str, b_text: str
) -> tuple[List[InlineChange], List[InlineChange]]:
    return _diff_tokens(list(a_text), list(b_text))


def _diff_tokens(
    a_tokens: List[str], b_tokens: List[str]
) -> tuple[List[InlineChange], List[InlineChange]]:
    matcher = SequenceMatcher(None, a_tokens, b_tokens, autojunk=False)
    a_changes: List[InlineChange] = []
    b_changes: List[InlineChange] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        a_segment = "".join(a_tokens[i1:i2])
        b_segment = "".join(b_tokens[j1:j2])
        if tag == "equal":
            if a_segment:
                a_changes.append(InlineChange(a_segment, DifferenceType.UNCHANGED))
            if b_segment:
                b_changes.append(InlineChange(b_segment, DifferenceType.UNCHANGED))
        elif tag == "delete":
            a_changes.append(InlineChange(a_segment, DifferenceType.REMOVED))
        elif tag == "insert":
            b_changes.append(InlineChange(b_segment, DifferenceType.ADDED))
        elif tag == "replace":
            if a_segment:
                a_changes.append(InlineChange(a_segment, DifferenceType.REMOVED))
            if b_segment:
                b_changes.append(InlineChange(b_segment, DifferenceType.ADDED))

    return a_changes, b_changes
