"""Character-level diffing.

Delegates to the shared token-diff implementation in `word_diff.py`
(character mode is just word mode with a token size of one character).
Kept as its own module per the architecture layout so the comparison
engine's mode dispatch (`LINE` / `WORD` / `CHARACTER`) maps 1:1 onto a
dedicated, discoverable module.
"""
from __future__ import annotations

from typing import List, Tuple

from app.comparison.word_diff import compute_inline_char_diff
from app.core.models import InlineChange

__all__ = ["compute_inline_char_diff", "diff_characters"]


def diff_characters(a_text: str, b_text: str) -> Tuple[List[InlineChange], List[InlineChange]]:
    return compute_inline_char_diff(a_text, b_text)
