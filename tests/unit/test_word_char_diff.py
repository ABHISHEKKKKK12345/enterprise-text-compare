from app.comparison.char_diff import diff_characters
from app.comparison.word_diff import compute_inline_word_diff
from app.core.enums import DifferenceType


def test_word_diff_identifies_changed_word():
    a_changes, b_changes = compute_inline_word_diff("the quick fox", "the slow fox")
    a_removed = [c.text for c in a_changes if c.change_type == DifferenceType.REMOVED]
    b_added = [c.text for c in b_changes if c.change_type == DifferenceType.ADDED]
    assert "quick" in a_removed
    assert "slow" in b_added


def test_word_diff_identical_lines_are_all_unchanged():
    a_changes, b_changes = compute_inline_word_diff("same text here", "same text here")
    assert all(c.change_type == DifferenceType.UNCHANGED for c in a_changes)
    assert all(c.change_type == DifferenceType.UNCHANGED for c in b_changes)


def test_char_diff_single_character_change():
    a_changes, b_changes = diff_characters("abcde", "abXde")
    a_removed = "".join(c.text for c in a_changes if c.change_type == DifferenceType.REMOVED)
    b_added = "".join(c.text for c in b_changes if c.change_type == DifferenceType.ADDED)
    assert a_removed == "c"
    assert b_added == "X"


def test_char_diff_empty_strings():
    a_changes, b_changes = diff_characters("", "")
    assert a_changes == []
    assert b_changes == []
