"""Application theming: Qt style sheets plus semantic diff colors.

Diff colors are exposed as a dict (not hard-coded inside widgets) so both
themes stay visually consistent and so a future high-contrast theme could
be added without touching widget code. Differences are never communicated
by color alone: the diff view widget also prefixes each row with a
+/-/~ glyph (see `diff_view.py`), satisfying the accessibility
requirement that color is not the sole indicator.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import Theme


@dataclass(frozen=True)
class DiffPalette:
    added_bg: str
    removed_bg: str
    modified_bg: str
    unchanged_fg: str
    inline_added_bg: str
    inline_removed_bg: str
    line_no_bg: str
    line_no_fg: str
    text_fg: str
    panel_bg: str
    border: str


LIGHT_PALETTE = DiffPalette(
    added_bg="#e6ffed",
    removed_bg="#ffeef0",
    modified_bg="#fff8e1",
    unchanged_fg="#6b7280",
    inline_added_bg="#abf2bc",
    inline_removed_bg="#fdb8c0",
    line_no_bg="#f3f4f6",
    line_no_fg="#9ca3af",
    text_fg="#1f2937",
    panel_bg="#ffffff",
    border="#e5e7eb",
)

DARK_PALETTE = DiffPalette(
    added_bg="#0f3324",
    removed_bg="#3a1219",
    modified_bg="#3a3116",
    unchanged_fg="#8b93a3",
    inline_added_bg="#1f6f43",
    inline_removed_bg="#7a2733",
    line_no_bg="#1c2128",
    line_no_fg="#6b7280",
    text_fg="#e5e7eb",
    panel_bg="#0d1117",
    border="#30363d",
)


def get_palette(theme: Theme) -> DiffPalette:
    return DARK_PALETTE if theme == Theme.DARK else LIGHT_PALETTE


_LIGHT_QSS = """
QWidget { background-color: #f5f6f8; color: #1f2937; font-size: 13px; }
QMainWindow { background-color: #f5f6f8; }
QToolBar { background-color: #ffffff; border-bottom: 1px solid #e5e7eb; spacing: 6px; padding: 4px; }
QStatusBar { background-color: #ffffff; border-top: 1px solid #e5e7eb; }
QGroupBox { font-weight: 600; border: 1px solid #e5e7eb; border-radius: 6px; margin-top: 10px; background: #ffffff; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton { background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 5px; padding: 6px 14px; }
QPushButton:hover { background-color: #f3f4f6; }
QPushButton:pressed { background-color: #e5e7eb; }
QPushButton:disabled { color: #9ca3af; }
QPushButton#primaryButton { background-color: #2563eb; color: white; border: none; font-weight: 600; }
QPushButton#primaryButton:hover { background-color: #1d4ed8; }
QPushButton#primaryButton:disabled { background-color: #93c5fd; }
QPushButton#dangerButton { background-color: #ffffff; color: #dc2626; border: 1px solid #fca5a5; }
QPushButton#dangerButton:hover { background-color: #fef2f2; }
QLineEdit, QPlainTextEdit, QTextEdit { background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 5px; padding: 4px; }
QTableView { background-color: #ffffff; gridline-color: #e5e7eb; border: 1px solid #e5e7eb; }
QTableView::item:selected { background-color: #1d4ed8; color: #ffffff; }
QTableView::item:selected:!active { background-color: #1d4ed8; color: #ffffff; }
QHeaderView::section { background-color: #f3f4f6; border: none; border-bottom: 1px solid #e5e7eb; padding: 4px; font-weight: 600; }
QTabWidget::pane { border: 1px solid #e5e7eb; }
QSplitter::handle { background-color: #e5e7eb; }
QProgressBar { border: 1px solid #d1d5db; border-radius: 5px; text-align: center; background: #ffffff; }
QProgressBar::chunk { background-color: #2563eb; border-radius: 5px; }
QLabel#appTitle { font-size: 15px; font-weight: 700; }
QLabel#versionLabel { color: #6b7280; font-size: 11px; }
QLabel#statHeading { font-weight: 600; }
QToolTip { background-color: #111827; color: white; border: none; padding: 4px 8px; }
QMenuBar { background-color: #ffffff; border-bottom: 1px solid #e5e7eb; padding: 2px 4px; spacing: 2px; }
QMenuBar::item { background: transparent; padding: 5px 10px; border-radius: 4px; }
QMenuBar::item:selected { background-color: #f3f4f6; }
QMenuBar::item:pressed { background-color: #e5e7eb; }
QMenu { background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 32px 6px 14px; border-radius: 4px; min-width: 160px; }
QMenu::item:selected { background-color: #2563eb; color: white; }
QMenu::item:disabled { color: #9ca3af; }
QMenu::separator { height: 1px; background-color: #e5e7eb; margin: 4px 8px; }
QMenu::indicator { width: 14px; height: 14px; margin-left: 4px; }
"""

_DARK_QSS = """
QWidget { background-color: #0d1117; color: #e5e7eb; font-size: 13px; }
QMainWindow { background-color: #0d1117; }
QToolBar { background-color: #161b22; border-bottom: 1px solid #30363d; spacing: 6px; padding: 4px; }
QStatusBar { background-color: #161b22; border-top: 1px solid #30363d; }
QGroupBox { font-weight: 600; border: 1px solid #30363d; border-radius: 6px; margin-top: 10px; background: #161b22; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton { background-color: #21262d; border: 1px solid #30363d; border-radius: 5px; padding: 6px 14px; color: #e5e7eb; }
QPushButton:hover { background-color: #30363d; }
QPushButton:pressed { background-color: #3a4048; }
QPushButton:disabled { color: #6b7280; }
QPushButton#primaryButton { background-color: #2f81f7; color: white; border: none; font-weight: 600; }
QPushButton#primaryButton:hover { background-color: #4c8ff9; }
QPushButton#primaryButton:disabled { background-color: #1f4a86; color: #9fb8dc;}
QPushButton#dangerButton { background-color: #21262d; color: #f85149; border: 1px solid #6e2c2c; }
QPushButton#dangerButton:hover { background-color: #3a1219; }
QLineEdit, QPlainTextEdit, QTextEdit { background-color: #0d1117; border: 1px solid #30363d; border-radius: 5px; padding: 4px; color: #e5e7eb; }
QTableView { background-color: #0d1117; gridline-color: #30363d; border: 1px solid #30363d; color: #e5e7eb; }
QTableView::item:selected { background-color: #4c8ff9; color: #0d1117; }
QTableView::item:selected:!active { background-color: #4c8ff9; color: #0d1117; }
QHeaderView::section { background-color: #161b22; border: none; border-bottom: 1px solid #30363d; padding: 4px; font-weight: 600; color: #e5e7eb; }
QTabWidget::pane { border: 1px solid #30363d; }
QSplitter::handle { background-color: #30363d; }
QProgressBar { border: 1px solid #30363d; border-radius: 5px; text-align: center; background: #0d1117; color: #e5e7eb; }
QProgressBar::chunk { background-color: #2f81f7; border-radius: 5px; }
QLabel#appTitle { font-size: 15px; font-weight: 700; }
QLabel#versionLabel { color: #8b93a3; font-size: 11px; }
QLabel#statHeading { font-weight: 600; }
QToolTip { background-color: #21262d; color: #e5e7eb; border: 1px solid #30363d; padding: 4px 8px; }
QMenuBar { background-color: #161b22; border-bottom: 1px solid #30363d; padding: 2px 4px; spacing: 2px; }
QMenuBar::item { background: transparent; padding: 5px 10px; border-radius: 4px; color: #e5e7eb; }
QMenuBar::item:selected { background-color: #30363d; }
QMenuBar::item:pressed { background-color: #3a4048; }
QMenu { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 4px; color: #e5e7eb; }
QMenu::item { padding: 6px 32px 6px 14px; border-radius: 4px; min-width: 160px; color: #e5e7eb; }
QMenu::item:selected { background-color: #2f81f7; color: white; }
QMenu::item:disabled { color: #6b7280; }
QMenu::separator { height: 1px; background-color: #30363d; margin: 4px 8px; }
QMenu::indicator { width: 14px; height: 14px; margin-left: 4px; }
"""


def get_stylesheet(theme: Theme) -> str:
    return _DARK_QSS if theme == Theme.DARK else _LIGHT_QSS
