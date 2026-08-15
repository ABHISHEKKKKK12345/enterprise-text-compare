"""Delegate that renders diff cell content, including inline (word/char)
highlight spans, using a lightweight `QTextDocument` for HTML rendering.

Falls back to plain text painting when there are no inline spans (LINE
mode), which is the common case and keeps that path fast.
"""
from __future__ import annotations

from html import escape

from PySide6.QtCore import QSize
from PySide6.QtGui import QAbstractTextDocumentLayout, QPalette, QTextDocument
from PySide6.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from app.core.enums import DifferenceType
from app.gui.styles.theme import DiffPalette
from app.gui.widgets.diff_table_model import INLINE_ROLE


class DiffItemDelegate(QStyledItemDelegate):
    def __init__(self, palette: DiffPalette, parent=None) -> None:
        super().__init__(parent)
        self._palette = palette

    def set_palette(self, palette: DiffPalette) -> None:
        self._palette = palette

    def initStyleOption(self, option: QStyleOptionViewItem, index) -> None:  # noqa: N802
        super().initStyleOption(option, index)
        # Bold text is an additional, non-color signal that a row is the
        # CURRENT/ACTIVE difference (as opposed to merely one of many
        # highlighted added/removed/modified rows), so the active row
        # remains identifiable even to users who cannot distinguish the
        # background-color difference.
        if option.state & QStyle.State_Selected:
            option.font.setBold(True)


    def _build_html(self, text: str, inline_changes) -> str:
        if not inline_changes:
            return escape(text)
        parts = []
        for change in inline_changes:
            safe = escape(change.text).replace(" ", "&nbsp;")
            if change.change_type == DifferenceType.ADDED:
                parts.append(
                    f'<span style="background-color:{self._palette.inline_added_bg};">{safe}</span>'
                )
            elif change.change_type == DifferenceType.REMOVED:
                parts.append(
                    f'<span style="background-color:{self._palette.inline_removed_bg};">{safe}</span>'
                )
            else:
                parts.append(safe)
        return "".join(parts)

    def paint(self, painter, option: QStyleOptionViewItem, index) -> None:  # noqa: N802
        inline_changes = index.data(INLINE_ROLE)
        if not inline_changes:
            super().paint(painter, option, index)
            return

        self.initStyleOption(option, index)
        style = option.widget.style() if option.widget else QApplication.style()

        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setHtml(self._build_html(option.text, inline_changes))
        doc.setTextWidth(option.rect.width())

        option.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, option, painter, option.widget)

        painter.save()
        painter.translate(option.rect.topLeft())
        ctx = QAbstractTextDocumentLayout.PaintContext()
        if option.state & QStyle.State_Selected:
            ctx.palette.setColor(QPalette.Text, option.palette.color(QPalette.HighlightedText))
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:  # noqa: N802
        inline_changes = index.data(INLINE_ROLE)
        if not inline_changes:
            return super().sizeHint(option, index)
        self.initStyleOption(option, index)
        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setHtml(self._build_html(option.text, inline_changes))
        doc.setTextWidth(option.rect.width() if option.rect.width() > 0 else 400)
        return QSize(int(doc.idealWidth()), int(doc.size().height()))
