"""SourcePanel — one side (A or B) of the input area.

Encapsulates all interaction for a single source: pasting/typing text,
opening a file (via dialog or drag-and-drop), clearing, copying, saving,
and displaying file metadata (encoding, size, line-ending style). Emits
plain Qt signals; the main window decides what to do with them (e.g.
routing file loads through a background worker), keeping this widget
free of I/O and threading concerns.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.models import FileMetadata
from app.utils.helpers import human_readable_size


class SourcePanel(QGroupBox):
    file_open_requested = Signal(Path)  # user picked/dropped a file
    text_changed = Signal()
    save_requested = Signal(str)  # current text content

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(title, parent)
        self.setAcceptDrops(True)
        self._file_metadata: Optional[FileMetadata] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        self.open_button = QPushButton("Open File\u2026")
        self.clear_button = QPushButton("Clear")
        self.copy_button = QPushButton("Copy")
        self.save_button = QPushButton("Save\u2026")
        for btn in (self.open_button, self.clear_button, self.copy_button, self.save_button):
            btn.setCursor(Qt.PointingHandCursor)
            toolbar.addWidget(btn)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText(
            "Paste text here, or open / drag a file (.txt, .log, .csv, .json, .xml, "
            ".html, .md, .yaml, source code, config files\u2026)"
        )
        self.text_edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.text_edit, 1)

        self.metadata_label = QLabel("No file loaded \u2014 paste text or open a file.")
        self.metadata_label.setObjectName("versionLabel")
        layout.addWidget(self.metadata_label)

        self.open_button.clicked.connect(self._handle_open_clicked)
        self.clear_button.clicked.connect(self.clear)
        self.copy_button.clicked.connect(self._handle_copy_clicked)
        self.save_button.clicked.connect(self._handle_save_clicked)
        self.text_edit.textChanged.connect(self.text_changed.emit)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def text(self) -> str:
        return self.text_edit.toPlainText()

    def set_text(self, text: str) -> None:
        self.text_edit.setPlainText(text)

    def clear(self) -> None:
        self.text_edit.clear()
        self._file_metadata = None
        self.metadata_label.setText("No file loaded \u2014 paste text or open a file.")

    def set_file_metadata(self, metadata: FileMetadata) -> None:
        self._file_metadata = metadata
        self.metadata_label.setText(
            f"{metadata.path.name} \u2022 {human_readable_size(metadata.size_bytes)} \u2022 "
            f"{metadata.encoding} ({metadata.encoding_confidence.value}) \u2022 "
            f"{metadata.line_ending.value.upper()}"
        )

    def set_busy(self, busy: bool) -> None:
        self.setEnabled(not busy)

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    def _handle_open_clicked(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)")
        if path_str:
            self.file_open_requested.emit(Path(path_str))

    def _handle_copy_clicked(self) -> None:
        self.text_edit.selectAll()
        self.text_edit.copy()
        cursor = self.text_edit.textCursor()
        cursor.clearSelection()
        self.text_edit.setTextCursor(cursor)

    def _handle_save_clicked(self) -> None:
        self.save_requested.emit(self.text())

    def trigger_save(self) -> None:
        """Public entry point so callers (e.g. a File menu action) can
        invoke the same Save behavior as clicking the panel's Save button."""
        self._handle_save_clicked()

    def trigger_open(self) -> None:
        """Public entry point mirroring the Open button, for menu reuse."""
        self._handle_open_clicked()

    def trigger_copy(self) -> None:
        """Public entry point mirroring the Copy button, for menu reuse."""
        self._handle_copy_clicked()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 (Qt override)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 (Qt override)
        urls = event.mimeData().urls()
        if urls:
            local_path = urls[0].toLocalFile()
            if local_path:
                self.file_open_requested.emit(Path(local_path))
                event.acceptProposedAction()
