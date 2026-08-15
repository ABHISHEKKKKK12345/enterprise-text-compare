import pytest

from app.core.exceptions import InvalidComparisonInputError
from app.core.models import ComparisonSettings
from app.services.comparison_service import ComparisonService


@pytest.fixture
def service():
    return ComparisonService()


def test_load_source_from_text(service):
    doc = service.load_source_from_text("hello\nworld\n", "My Source")
    assert doc.label == "My Source"
    assert doc.line_count == 2


def test_load_source_from_file(service, tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("line1\nline2\n", encoding="utf-8")
    doc = service.load_source_from_file(path, "Source A", huge_file_threshold=10 * 1024 * 1024)
    assert doc.text == "line1\nline2\n"
    assert doc.file_metadata is not None


def test_full_compare_workflow_from_files(service, tmp_path):
    path_a = tmp_path / "a.txt"
    path_b = tmp_path / "b.txt"
    path_a.write_text("one\ntwo\nthree\n", encoding="utf-8")
    path_b.write_text("one\nTWO\nthree\nfour\n", encoding="utf-8")

    doc_a = service.load_source_from_file(path_a, "A", huge_file_threshold=10_000_000)
    doc_b = service.load_source_from_file(path_b, "B", huge_file_threshold=10_000_000)

    result = service.compare(doc_a, doc_b, ComparisonSettings())
    assert result.statistics.added == 1
    assert result.statistics.modified == 1


def test_compare_rejects_none_sources(service):
    with pytest.raises(InvalidComparisonInputError):
        service.compare(None, None, ComparisonSettings())


def test_progress_and_cancellation_wiring(service):
    doc_a = service.load_source_from_text("\n".join(str(i) for i in range(2000)), "A")
    doc_b = service.load_source_from_text("\n".join(str(i) for i in range(2000)), "B")
    seen = []
    result = service.compare(
        doc_a, doc_b, ComparisonSettings(), on_progress=seen.append, is_cancelled=lambda: False
    )
    assert result.statistics.is_identical
    assert seen
