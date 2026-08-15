"""DiffView — the professional side-by-side result viewer.

Combines the `DiffTableModel`/`DiffItemDelegate` with a toolbar
(search, next/prev/first/last difference navigation, font zoom) and a
statistics bar showing the Added/Removed/Modified/Unchanged summary.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import DEFAULT_FONT_SIZE, MAX_FONT_SIZE, MIN_FONT_SIZE
from app.core.enums import DifferenceType, Theme
from app.core.models import ComparisonResult
from app.gui.styles.theme import get_palette
from app.gui.widgets.diff_delegate import DiffItemDelegate
from app.gui.widgets.diff_table_model import DiffTableModel
from app.utils.helpers import clamp


class DiffView(QWidget):
    difference_position_changed = Signal(int, int)  # current (1-based), total

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._font_size = DEFAULT_FONT_SIZE
        self._font_family = "Consolas"
        self._diff_row_indices: List[int] = []  # rows that are not UNCHANGED
        self._current_diff_pos: int = -1  # index into _diff_row_indices
        self._search_matches: List[int] = []
        self._search_pos: int = -1
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search in results\u2026 (Ctrl+F)")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setMaximumWidth(260)
        toolbar.addWidget(self.search_box)

        self.search_prev_btn = QToolButton()
        self.search_prev_btn.setText("\u2191")
        self.search_prev_btn.setToolTip("Previous match (Shift+F3)")
        self.search_next_btn = QToolButton()
        self.search_next_btn.setText("\u2193")
        self.search_next_btn.setToolTip("Next match (F3)")
        toolbar.addWidget(self.search_prev_btn)
        toolbar.addWidget(self.search_next_btn)
        self.search_status_label = QLabel("")
        toolbar.addWidget(self.search_status_label)

        toolbar.addStretch(1)

        self.first_diff_btn = QToolButton()
        self.first_diff_btn.setText("\u23ee")
        self.first_diff_btn.setToolTip("First difference (Ctrl+Home)")
        self.prev_diff_btn = QToolButton()
        self.prev_diff_btn.setText("\u25c0")
        self.prev_diff_btn.setToolTip("Previous difference (Ctrl+Up)")
        self.next_diff_btn = QToolButton()
        self.next_diff_btn.setText("\u25b6")
        self.next_diff_btn.setToolTip("Next difference (Ctrl+Down)")
        self.last_diff_btn = QToolButton()
        self.last_diff_btn.setText("\u23ed")
        self.last_diff_btn.setToolTip("Last difference (Ctrl+End)")
        self.diff_position_label = QLabel("No differences")
        for btn in (self.first_diff_btn, self.prev_diff_btn, self.next_diff_btn, self.last_diff_btn):
            toolbar.addWidget(btn)
        toolbar.addWidget(self.diff_position_label)

        toolbar.addStretch(1)

        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setText("A-")
        self.zoom_out_btn.setToolTip("Decrease font size")
        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setText("A+")
        self.zoom_in_btn.setToolTip("Increase font size")
        self.copy_diff_btn = QPushButton("Copy Difference")
        toolbar.addWidget(self.zoom_out_btn)
        toolbar.addWidget(self.zoom_in_btn)
        toolbar.addWidget(self.copy_diff_btn)

        layout.addLayout(toolbar)

        self._palette = get_palette(Theme.LIGHT)
        self.model = DiffTableModel(self._palette)
        self.delegate = DiffItemDelegate(self._palette)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setItemDelegateForColumn(1, self.delegate)
        self.table.setItemDelegateForColumn(3, self.delegate)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 55)
        self.table.setColumnWidth(2, 55)
        self.table.setColumnWidth(1, 480)
        self.table.setColumnWidth(3, 480)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)
        self._apply_font_size()
        layout.addWidget(self.table, 1)

        self.stats_bar = QLabel("Select two sources and click Compare to see results.")
        self.stats_bar.setObjectName("statHeading")
        layout.addWidget(self.stats_bar)

        # Wiring
        self.search_next_btn.clicked.connect(lambda: self._advance_search(1))
        self.search_prev_btn.clicked.connect(lambda: self._advance_search(-1))
        self.search_box.returnPressed.connect(lambda: self._advance_search(1))
        self.search_box.textChanged.connect(self._recompute_search_matches)

        self.first_diff_btn.clicked.connect(self.go_to_first_difference)
        self.prev_diff_btn.clicked.connect(self.go_to_previous_difference)
        self.next_diff_btn.clicked.connect(self.go_to_next_difference)
        self.last_diff_btn.clicked.connect(self.go_to_last_difference)

        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.copy_diff_btn.clicked.connect(self._copy_current_row)

        QShortcut(QKeySequence("F3"), self, activated=lambda: self._advance_search(1))
        QShortcut(QKeySequence("Shift+F3"), self, activated=lambda: self._advance_search(-1))
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.search_box.setFocus)
        QShortcut(QKeySequence("Ctrl+Down"), self, activated=self.go_to_next_difference)
        QShortcut(QKeySequence("Ctrl+Up"), self, activated=self.go_to_previous_difference)
        QShortcut(QKeySequence("Ctrl+Home"), self, activated=self.go_to_first_difference)
        QShortcut(QKeySequence("Ctrl+End"), self, activated=self.go_to_last_difference)
        QShortcut(QKeySequence("Escape"), self.search_box, activated=self._close_search)

        self._update_navigation_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_result(self, result: ComparisonResult) -> None:
        self.model.set_differences(result.differences)
        self._diff_row_indices = [
            i for i, d in enumerate(result.differences) if d.change_type != DifferenceType.UNCHANGED
        ]
        self._current_diff_pos = -1
        self._search_matches = []
        self._search_pos = -1
        stats = result.statistics
        self.stats_bar.setText(
            f"Lines Compared: {stats.lines_compared}    "
            f"Added: {stats.added}    Removed: {stats.removed}    "
            f"Modified: {stats.modified}    Unchanged: {stats.unchanged}    "
            f"({result.duration_seconds:.2f}s)"
        )
        self._update_navigation_state()
        if self._diff_row_indices:
            self.go_to_first_difference()
        elif self.model.rowCount():
            self.table.selectRow(0)

    def clear(self) -> None:
        self.model.set_differences([])
        self._diff_row_indices = []
        self._current_diff_pos = -1
        self.stats_bar.setText("Select two sources and click Compare to see results.")
        self._update_navigation_state()

    def apply_theme(self, theme: Theme) -> None:
        self._palette = get_palette(theme)
        self.model.set_palette(self._palette)
        self.delegate.set_palette(self._palette)
        self.table.viewport().update()

    def set_font_size(self, size: int) -> None:
        self._font_size = clamp(size, MIN_FONT_SIZE, MAX_FONT_SIZE)
        self._apply_font_size()

    @property
    def font_size(self) -> int:
        return self._font_size

    def zoom_in(self) -> None:
        self.set_font_size(self._font_size + 1)

    def zoom_out(self) -> None:
        self.set_font_size(self._font_size - 1)

    def reset_zoom(self) -> None:
        self.set_font_size(DEFAULT_FONT_SIZE)

    def set_font_family(self, family: str) -> None:
        self._font_family = family
        self._apply_font_size()

    # ------------------------------------------------------------------
    # Difference navigation
    # ------------------------------------------------------------------

    def go_to_first_difference(self) -> None:
        if self._diff_row_indices:
            self._current_diff_pos = 0
            self._select_row(self._diff_row_indices[0])
        self._update_navigation_state()

    def go_to_last_difference(self) -> None:
        if self._diff_row_indices:
            self._current_diff_pos = len(self._diff_row_indices) - 1
            self._select_row(self._diff_row_indices[-1])
        self._update_navigation_state()

    def go_to_next_difference(self) -> None:
        if not self._diff_row_indices:
            return
        self._current_diff_pos = min(self._current_diff_pos + 1, len(self._diff_row_indices) - 1)
        self._select_row(self._diff_row_indices[self._current_diff_pos])
        self._update_navigation_state()

    def go_to_previous_difference(self) -> None:
        if not self._diff_row_indices:
            return
        self._current_diff_pos = max(self._current_diff_pos - 1, 0)
        self._select_row(self._diff_row_indices[self._current_diff_pos])
        self._update_navigation_state()

    def _select_row(self, row: int) -> None:
        index = self.model.index(row, 1)
        self.table.setCurrentIndex(index)
        self.table.scrollTo(index, QAbstractItemView.PositionAtCenter)

    def _update_navigation_state(self) -> None:
        total = len(self._diff_row_indices)
        has_diffs = total > 0
        for btn in (self.first_diff_btn, self.prev_diff_btn, self.next_diff_btn, self.last_diff_btn):
            btn.setEnabled(has_diffs)
        if has_diffs:
            pos = self._current_diff_pos if self._current_diff_pos >= 0 else 0
            self.diff_position_label.setText(f"Difference {pos + 1} of {total}")
            self.difference_position_changed.emit(pos + 1, total)
        else:
            self.diff_position_label.setText("No differences" if self.model.rowCount() else "")
            self.difference_position_changed.emit(0, 0)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _recompute_search_matches(self, text: str) -> None:
        self._search_matches = []
        self._search_pos = -1
        if not text:
            self.search_status_label.setText("")
            return
        needle = text.lower()
        for row in range(self.model.rowCount()):
            a_text = self.model.index(row, 1).data() or ""
            b_text = self.model.index(row, 3).data() or ""
            if needle in a_text.lower() or needle in b_text.lower():
                self._search_matches.append(row)
        self.search_status_label.setText(
            f"{len(self._search_matches)} match(es)" if self._search_matches else "No matches"
        )

    def _advance_search(self, direction: int) -> None:
        if not self._search_matches:
            self._recompute_search_matches(self.search_box.text())
        if not self._search_matches:
            return
        self._search_pos = (self._search_pos + direction) % len(self._search_matches)
        row = self._search_matches[self._search_pos]
        self._select_row(row)
        self.search_status_label.setText(
            f"Match {self._search_pos + 1} of {len(self._search_matches)}"
        )

    def _close_search(self) -> None:
        """Clear and dismiss the search box (Escape), returning focus to
        the results table without disturbing difference navigation state."""
        self.search_box.clear()
        self._search_matches = []
        self._search_pos = -1
        self.search_status_label.setText("")
        self.table.setFocus()

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def _apply_font_size(self) -> None:
        font = QFont()
        font.setFamilies([f.strip(" '\"") for f in self._font_family.split(",")])
        font.setPointSize(self._font_size)
        font.setStyleHint(QFont.Monospace)
        self.table.setFont(font)
        self.table.resizeRowsToContents()

    def _copy_current_row(self) -> None:
        index = self.table.currentIndex()
        if not index.isValid():
            return
        diff = self.model.difference_at(index.row())
        if diff is None:
            return
        from PySide6.QtWidgets import QApplication

        text = diff.a_text if diff.change_type == DifferenceType.REMOVED else diff.b_text
        if diff.change_type == DifferenceType.MODIFIED:
            text = f"A: {diff.a_text}\nB: {diff.b_text}"
        QApplication.clipboard().setText(text)
