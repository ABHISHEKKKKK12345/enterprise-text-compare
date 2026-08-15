"""ExportService — turns a `ComparisonResult` into a report file.

Every exporter is a pure function of the `ComparisonResult`; none of them
touch the original source files (export is strictly a read of in-memory
results, never a rewrite of user documents).
"""
from __future__ import annotations

import csv
import io
import json
import logging
from html import escape
from pathlib import Path

from app.core.enums import DifferenceType, ExportFormat
from app.core.exceptions import ExportError
from app.core.models import ComparisonResult
from app.io.file_writer import write_text_atomic

logger = logging.getLogger(__name__)

_DIFF_LABEL = {
    DifferenceType.ADDED: "Added",
    DifferenceType.REMOVED: "Removed",
    DifferenceType.MODIFIED: "Modified",
    DifferenceType.UNCHANGED: "Unchanged",
}


class ExportService:
    def export(self, result: ComparisonResult, path: Path, fmt: ExportFormat) -> None:
        try:
            if fmt == ExportFormat.HTML:
                content = self._render_html(result)
            elif fmt == ExportFormat.TXT:
                content = self._render_txt(result)
            elif fmt == ExportFormat.JSON:
                content = self._render_json(result)
            elif fmt == ExportFormat.CSV:
                content = self._render_csv(result)
            elif fmt == ExportFormat.MARKDOWN:
                content = self._render_markdown(result)
            else:
                raise ExportError(f"Unsupported export format: {fmt}")
        except ExportError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ExportError(
                "Unable to generate the export report due to an internal error.", cause=exc
            ) from exc

        write_text_atomic(path, content)
        logger.info("Exported comparison result to %s as %s", path, fmt.value)

    # ------------------------------------------------------------------
    # Renderers
    # ------------------------------------------------------------------

    def _render_txt(self, result: ComparisonResult) -> str:
        req = result.request
        lines = [
            "ENTERPRISE TEXT COMPARE - COMPARISON REPORT",
            "=" * 60,
            f"Generated: {result.generated_at.isoformat(timespec='seconds')}",
            f"Source A: {req.source_a.label}",
            f"Source B: {req.source_b.label}",
            f"Settings: {req.settings.normalized_copy_note()}",
            "-" * 60,
            f"Lines Compared: {result.statistics.lines_compared}",
            f"Added:          {result.statistics.added}",
            f"Removed:        {result.statistics.removed}",
            f"Modified:       {result.statistics.modified}",
            f"Unchanged:      {result.statistics.unchanged}",
            "-" * 60,
            "",
        ]
        for diff in result.differences:
            if diff.change_type == DifferenceType.UNCHANGED:
                continue
            prefix = {
                DifferenceType.ADDED: "+",
                DifferenceType.REMOVED: "-",
                DifferenceType.MODIFIED: "~",
            }[diff.change_type]
            a_no = diff.a_line_no if diff.a_line_no is not None else "-"
            b_no = diff.b_line_no if diff.b_line_no is not None else "-"
            lines.append(f"[{prefix}] A:{a_no} / B:{b_no}")
            if diff.change_type in (DifferenceType.REMOVED, DifferenceType.MODIFIED):
                lines.append(f"    A: {diff.a_text}")
            if diff.change_type in (DifferenceType.ADDED, DifferenceType.MODIFIED):
                lines.append(f"    B: {diff.b_text}")
        return "\n".join(lines) + "\n"

    def _render_json(self, result: ComparisonResult) -> str:
        req = result.request
        payload = {
            "generated_at": result.generated_at.isoformat(),
            "duration_seconds": result.duration_seconds,
            "source_a": {"label": req.source_a.label, "line_count": req.source_a.line_count},
            "source_b": {"label": req.source_b.label, "line_count": req.source_b.line_count},
            "settings": {
                "mode": req.settings.mode.value,
                "case_sensitive": req.settings.case_sensitive,
                "ignore_leading_trailing_whitespace": req.settings.ignore_leading_trailing_whitespace,
                "ignore_repeated_spaces": req.settings.ignore_repeated_spaces,
                "ignore_blank_lines": req.settings.ignore_blank_lines,
                "ignore_line_ending_differences": req.settings.ignore_line_ending_differences,
                "normalize_unicode": req.settings.normalize_unicode,
            },
            "statistics": {
                "lines_compared": result.statistics.lines_compared,
                "added": result.statistics.added,
                "removed": result.statistics.removed,
                "modified": result.statistics.modified,
                "unchanged": result.statistics.unchanged,
            },
            "differences": [
                {
                    "index": d.index,
                    "type": d.change_type.value,
                    "a_line_no": d.a_line_no,
                    "b_line_no": d.b_line_no,
                    "a_text": d.a_text,
                    "b_text": d.b_text,
                }
                for d in result.differences
                if d.change_type != DifferenceType.UNCHANGED
            ],
        }
        return json.dumps(payload, indent=2)

    def _render_csv(self, result: ComparisonResult) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["type", "a_line_no", "b_line_no", "a_text", "b_text"])
        for d in result.differences:
            if d.change_type == DifferenceType.UNCHANGED:
                continue
            writer.writerow(
                [d.change_type.value, d.a_line_no or "", d.b_line_no or "", d.a_text, d.b_text]
            )
        return buffer.getvalue()

    def _render_markdown(self, result: ComparisonResult) -> str:
        req = result.request
        lines = [
            "# Comparison Report",
            "",
            f"- **Generated:** {result.generated_at.isoformat(timespec='seconds')}",
            f"- **Source A:** {req.source_a.label}",
            f"- **Source B:** {req.source_b.label}",
            f"- **Settings:** {req.settings.normalized_copy_note()}",
            "",
            "| Metric | Count |",
            "|---|---|",
            f"| Lines Compared | {result.statistics.lines_compared} |",
            f"| Added | {result.statistics.added} |",
            f"| Removed | {result.statistics.removed} |",
            f"| Modified | {result.statistics.modified} |",
            f"| Unchanged | {result.statistics.unchanged} |",
            "",
            "## Differences",
            "",
        ]
        for d in result.differences:
            if d.change_type == DifferenceType.UNCHANGED:
                continue
            lines.append(f"### {_DIFF_LABEL[d.change_type]} (A:{d.a_line_no or '-'} / B:{d.b_line_no or '-'})")
            if d.a_text:
                lines.append(f"- A: `{d.a_text}`")
            if d.b_text:
                lines.append(f"- B: `{d.b_text}`")
            lines.append("")
        return "\n".join(lines)

    def _render_html(self, result: ComparisonResult) -> str:
        req = result.request
        rows = []
        for d in result.differences:
            css_class = d.change_type.value
            a_no = d.a_line_no if d.a_line_no is not None else ""
            b_no = d.b_line_no if d.b_line_no is not None else ""
            rows.append(
                f'<tr class="{css_class}">'
                f'<td class="lineno">{a_no}</td><td class="content">{escape(d.a_text)}</td>'
                f'<td class="lineno">{b_no}</td><td class="content">{escape(d.b_text)}</td>'
                f"</tr>"
            )
        rows_html = "\n".join(rows)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Enterprise Text Compare - Report</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; color: #1a1a1a; background: #fafafa; }}
  h1 {{ font-size: 20px; }}
  .meta {{ color: #555; font-size: 13px; margin-bottom: 16px; }}
  .stats {{ display: flex; gap: 16px; margin-bottom: 20px; }}
  .stat {{ background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 8px 14px; font-size: 13px; }}
  table {{ border-collapse: collapse; width: 100%; font-family: Consolas, monospace; font-size: 12.5px; background: #fff; }}
  td {{ border: 1px solid #e0e0e0; padding: 4px 8px; vertical-align: top; }}
  td.lineno {{ width: 40px; color: #888; text-align: right; background: #f5f5f5; }}
  tr.added td.content {{ background: #e6ffed; }}
  tr.removed td.content {{ background: #ffeef0; }}
  tr.modified td.content {{ background: #fff8e1; }}
  tr.unchanged td.content {{ color: #999; }}
</style>
</head>
<body>
  <h1>Enterprise Text Compare &mdash; Comparison Report</h1>
  <div class="meta">
    Generated {escape(result.generated_at.isoformat(timespec='seconds'))} &middot;
    Source A: {escape(req.source_a.label)} &middot;
    Source B: {escape(req.source_b.label)} &middot;
    Settings: {escape(req.settings.normalized_copy_note())}
  </div>
  <div class="stats">
    <div class="stat">Lines Compared: {result.statistics.lines_compared}</div>
    <div class="stat">Added: {result.statistics.added}</div>
    <div class="stat">Removed: {result.statistics.removed}</div>
    <div class="stat">Modified: {result.statistics.modified}</div>
    <div class="stat">Unchanged: {result.statistics.unchanged}</div>
  </div>
  <table>
    <thead><tr><th>A#</th><th>Source A</th><th>B#</th><th>Source B</th></tr></thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</body>
</html>
"""
