from app.comparison.normalization import apply_settings_to_line, normalize_line_endings
from app.core.models import ComparisonSettings


def test_normalize_line_endings_crlf():
    assert normalize_line_endings("a\r\nb\r\n") == "a\nb\n"


def test_normalize_line_endings_cr():
    assert normalize_line_endings("a\rb\r") == "a\nb\n"


def test_apply_settings_case_fold():
    settings = ComparisonSettings(case_sensitive=False)
    assert apply_settings_to_line("HELLO", settings) == "hello"


def test_apply_settings_strip():
    settings = ComparisonSettings(ignore_leading_trailing_whitespace=True)
    assert apply_settings_to_line("  hi  ", settings) == "hi"


def test_apply_settings_collapse_spaces():
    settings = ComparisonSettings(ignore_repeated_spaces=True)
    assert apply_settings_to_line("a    b   c", settings) == "a b c"


def test_apply_settings_noop_by_default():
    settings = ComparisonSettings()
    assert apply_settings_to_line("  Hello  World  ", settings) == "  Hello  World  "
