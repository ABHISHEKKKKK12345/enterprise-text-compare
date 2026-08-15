from app.comparison.engine import ComparisonEngine
from app.core.enums import ComparisonMode, DifferenceType, SourceOrigin
from app.core.models import ComparisonSettings, SourceDocument

engine = ComparisonEngine()


def doc(text: str, label: str = "A") -> SourceDocument:
    return SourceDocument(label=label, text=text, origin=SourceOrigin.PASTED_TEXT)


def test_identical_files_report_no_differences():
    result = engine.compare(doc("a\nb\nc\n"), doc("a\nb\nc\n"), ComparisonSettings())
    assert result.statistics.is_identical
    assert result.statistics.added == 0
    assert result.statistics.removed == 0
    assert result.statistics.modified == 0


def test_completely_different_files():
    result = engine.compare(doc("x\ny\n"), doc("p\nq\n"), ComparisonSettings())
    assert result.statistics.modified == 2 or (
        result.statistics.added + result.statistics.removed == 4
    )


def test_added_lines_detected():
    result = engine.compare(doc("a\nb\n"), doc("a\nb\nc\n"), ComparisonSettings())
    assert result.statistics.added == 1
    added = [d for d in result.differences if d.change_type == DifferenceType.ADDED]
    assert added[0].b_text == "c"


def test_removed_lines_detected():
    result = engine.compare(doc("a\nb\nc\n"), doc("a\nc\n"), ComparisonSettings())
    assert result.statistics.removed == 1
    removed = [d for d in result.differences if d.change_type == DifferenceType.REMOVED]
    assert removed[0].a_text == "b"


def test_modified_line_detected():
    result = engine.compare(doc("hello world\n"), doc("hello there\n"), ComparisonSettings())
    assert result.statistics.modified == 1


def test_empty_vs_empty():
    result = engine.compare(doc(""), doc(""), ComparisonSettings())
    assert result.statistics.lines_compared == 0
    assert result.statistics.is_identical


def test_empty_vs_nonempty():
    result = engine.compare(doc(""), doc("a\nb\n"), ComparisonSettings())
    assert result.statistics.added == 2


def test_empty_lines_are_compared_by_default():
    result = engine.compare(doc("a\n\nb\n"), doc("a\nb\n"), ComparisonSettings())
    assert not result.statistics.is_identical


def test_ignore_blank_lines_setting():
    settings = ComparisonSettings(ignore_blank_lines=True)
    result = engine.compare(doc("a\n\nb\n"), doc("a\nb\n"), settings)
    assert result.statistics.is_identical


def test_case_sensitivity_default_is_sensitive():
    result = engine.compare(doc("Hello\n"), doc("hello\n"), ComparisonSettings())
    assert not result.statistics.is_identical


def test_case_insensitive_setting():
    settings = ComparisonSettings(case_sensitive=False)
    result = engine.compare(doc("Hello\n"), doc("hello\n"), settings)
    assert result.statistics.is_identical


def test_ignore_leading_trailing_whitespace():
    settings = ComparisonSettings(ignore_leading_trailing_whitespace=True)
    result = engine.compare(doc("  hello  \n"), doc("hello\n"), settings)
    assert result.statistics.is_identical


def test_ignore_repeated_spaces():
    settings = ComparisonSettings(ignore_repeated_spaces=True)
    result = engine.compare(doc("a    b\n"), doc("a b\n"), settings)
    assert result.statistics.is_identical


def test_crlf_vs_lf_ignored_by_default():
    settings = ComparisonSettings(ignore_line_ending_differences=True)
    result = engine.compare(doc("a\r\nb\r\n"), doc("a\nb\n"), settings)
    assert result.statistics.is_identical


def test_unicode_normalization():
    # 'é' as single codepoint (NFC) vs 'e' + combining acute accent (NFD)
    nfc = "café\n"
    nfd = "cafe\u0301\n"
    settings = ComparisonSettings(normalize_unicode=True)
    result = engine.compare(doc(nfc), doc(nfd), settings)
    assert result.statistics.is_identical


def test_emoji_and_special_characters():
    result = engine.compare(doc("hello 🚀\n"), doc("hello 🚀\n"), ComparisonSettings())
    assert result.statistics.is_identical
    result2 = engine.compare(doc("hello 🚀\n"), doc("hello 🔥\n"), ComparisonSettings())
    assert not result2.statistics.is_identical


def test_word_mode_inline_changes_present():
    settings = ComparisonSettings(mode=ComparisonMode.WORD)
    result = engine.compare(doc("the quick fox\n"), doc("the slow fox\n"), settings)
    modified = [d for d in result.differences if d.change_type == DifferenceType.MODIFIED]
    assert modified
    assert any(ic.text.strip() for ic in modified[0].a_inline)
    assert any(ic.text.strip() for ic in modified[0].b_inline)


def test_character_mode_inline_changes_present():
    settings = ComparisonSettings(mode=ComparisonMode.CHARACTER)
    result = engine.compare(doc("abcde\n"), doc("abXde\n"), settings)
    modified = [d for d in result.differences if d.change_type == DifferenceType.MODIFIED]
    assert modified
    assert modified[0].a_inline
    assert modified[0].b_inline


def test_large_input_performance_smoke():
    lines_a = "\n".join(f"line {i}" for i in range(20000)) + "\n"
    lines_b = "\n".join(f"line {i}" if i % 500 else f"CHANGED {i}" for i in range(20000)) + "\n"
    result = engine.compare(doc(lines_a), doc(lines_b), ComparisonSettings())
    assert result.statistics.lines_compared == 20000
    assert result.statistics.modified == 40


def test_cancellation_raises():
    from app.core.exceptions import ComparisonCancelledError

    big_a = "\n".join(str(i) for i in range(5000))
    big_b = "\n".join(str(i) + "x" for i in range(5000))
    try:
        engine.compare(
            doc(big_a), doc(big_b), ComparisonSettings(), is_cancelled=lambda: True
        )
        assert False, "expected cancellation"
    except ComparisonCancelledError:
        pass


def test_progress_callback_invoked():
    calls = []
    lines_a = "\n".join(str(i) for i in range(1000))
    lines_b = "\n".join(str(i) for i in range(1000))
    engine.compare(doc(lines_a), doc(lines_b), ComparisonSettings(), on_progress=calls.append)
    assert calls
    assert calls[-1] == 100
