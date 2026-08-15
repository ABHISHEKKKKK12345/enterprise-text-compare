import json

import pytest

from app.comparison.engine import ComparisonEngine
from app.core.enums import ExportFormat, SourceOrigin
from app.core.exceptions import ExportError
from app.core.models import ComparisonSettings, SourceDocument
from app.services.export_service import ExportService


@pytest.fixture
def sample_result():
    engine = ComparisonEngine()
    a = SourceDocument("A", "one\ntwo\nthree\n", SourceOrigin.PASTED_TEXT)
    b = SourceDocument("B", "one\nTWO\nthree\nfour\n", SourceOrigin.PASTED_TEXT)
    return engine.compare(a, b, ComparisonSettings())


def test_export_html(tmp_path, sample_result):
    svc = ExportService()
    path = tmp_path / "report.html"
    svc.export(sample_result, path, ExportFormat.HTML)
    content = path.read_text(encoding="utf-8")
    assert "<html" in content
    assert "Comparison Report" in content
    assert "Added: 1" in content


def test_export_txt(tmp_path, sample_result):
    svc = ExportService()
    path = tmp_path / "report.txt"
    svc.export(sample_result, path, ExportFormat.TXT)
    content = path.read_text(encoding="utf-8")
    assert "Lines Compared" in content


def test_export_json_is_valid_and_structured(tmp_path, sample_result):
    svc = ExportService()
    path = tmp_path / "report.json"
    svc.export(sample_result, path, ExportFormat.JSON)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["statistics"]["added"] == 1
    assert isinstance(payload["differences"], list)


def test_export_csv(tmp_path, sample_result):
    svc = ExportService()
    path = tmp_path / "report.csv"
    svc.export(sample_result, path, ExportFormat.CSV)
    content = path.read_text(encoding="utf-8")
    assert "type,a_line_no,b_line_no,a_text,b_text" in content


def test_export_markdown(tmp_path, sample_result):
    svc = ExportService()
    path = tmp_path / "report.md"
    svc.export(sample_result, path, ExportFormat.MARKDOWN)
    content = path.read_text(encoding="utf-8")
    assert "# Comparison Report" in content


def test_export_does_not_modify_original_sources(tmp_path, sample_result):
    original_a = sample_result.request.source_a.text
    original_b = sample_result.request.source_b.text
    svc = ExportService()
    svc.export(sample_result, tmp_path / "r.html", ExportFormat.HTML)
    assert sample_result.request.source_a.text == original_a
    assert sample_result.request.source_b.text == original_b
