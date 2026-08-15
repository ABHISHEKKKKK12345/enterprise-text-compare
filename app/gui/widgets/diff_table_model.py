"""Qt table model wrapping a `ComparisonResult`'s differences.

A single `QTableView` with four columns (A#, Source A, B#, Source B) is
used instead of two separately-scrolled views: this makes "synchronized
scrolling" trivial and correct by construction (there is only one
scrollbar, so the two sides can never drift out of alignment) while still
presenting a clear side-by-side layout.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.core.enums import DifferenceType
from app.core.models import Difference
from app.gui.styles.theme import DiffPalette

_COLUMNS = ["A#", "Source A", "B#", "Source B"]

INLINE_ROLE = Qt.UserRole + 1
CHANGE_TYPE_ROLE = Qt.UserRole + 2


class DiffTableModel(QAbstractTableModel):
    def __init__(self, palette: DiffPalette, parent=None) -> None:
        super().__init__(parent)
        self._differences: List[Difference] = []
        self._palette = palette

    def set_differences(self, differences: List[Difference]) -> None:
        self.beginResetModel()
        self._differences = differences
        self.endResetModel()

    def set_palette(self, palette: DiffPalette) -> None:
        self._palette = palette
        if self._differences:
            top_left = self.index(0, 0)
            bottom_right = self.index(self.rowCount() - 1, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right)

    def difference_at(self, row: int) -> Optional[Difference]:
        if 0 <= row < len(self._differences):
            return self._differences[row]
        return None

    @staticmethod
    def _line_no_label(line_no: Optional[int], change_type: DifferenceType, side: str) -> str:
        """Line-number cell text, prefixed with a non-color glyph indicator
        (+/-/~) so difference type is never communicated by background
        color alone. Unchanged rows show a plain number with no glyph to
        keep the common case visually quiet.
        """
        if line_no is None:
            return ""
        glyph = {
            DifferenceType.ADDED: "+",
            DifferenceType.REMOVED: "\u2212",  # minus sign (distinct from hyphen)
            DifferenceType.MODIFIED: "~",
        }.get(change_type)
        return f"{glyph} {line_no}" if glyph else str(line_no)

    # -- QAbstractTableModel overrides -----------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._differences)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(_COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        return _COLUMNS[section]

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None
        diff = self._differences[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return self._line_no_label(diff.a_line_no, diff.change_type, side="a")
            if col == 1:
                return diff.a_text
            if col == 2:
                return self._line_no_label(diff.b_line_no, diff.change_type, side="b")
            if col == 3:
                return diff.b_text
        elif role == Qt.BackgroundRole:
            return self._background_for(diff.change_type, is_line_number_col=col in (0, 2))
        elif role == Qt.ForegroundRole:
            if diff.change_type == DifferenceType.UNCHANGED:
                from PySide6.QtGui import QColor

                return QColor(self._palette.unchanged_fg)
        elif role == INLINE_ROLE:
            if col == 1:
                return diff.a_inline
            if col == 3:
                return diff.b_inline
        elif role == CHANGE_TYPE_ROLE:
            return diff.change_type
        return None

    def _background_for(self, change_type: DifferenceType, is_line_number_col: bool):
        from PySide6.QtGui import QColor

        if is_line_number_col:
            return QColor(self._palette.line_no_bg)
        mapping = {
            DifferenceType.ADDED: self._palette.added_bg,
            DifferenceType.REMOVED: self._palette.removed_bg,
            DifferenceType.MODIFIED: self._palette.modified_bg,
        }
        color = mapping.get(change_type)
        return QColor(color) if color else QColor(self._palette.panel_bg)
