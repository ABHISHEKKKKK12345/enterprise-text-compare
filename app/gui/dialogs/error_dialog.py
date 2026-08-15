"""Error dialog shown for any handled or unexpected exception.

Never shows a raw traceback by default — only the friendly
`ErrorInformation.user_message` and the error ID. Technical detail is
available behind an explicit "Technical Details" toggle, and the error ID
can be copied to the clipboard for support purposes.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from app.core.models import ErrorInformation


class ErrorDialog(QDialog):
    def __init__(self, info: ErrorInformation, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("An Error Occurred")
        self.setMinimumWidth(460)
        self._info = info
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        message_label = QLabel(self._info.user_message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        id_row = QHBoxLayout()
        id_label = QLabel(f"Error ID: {self._info.error_id}")
        id_label.setObjectName("versionLabel")
        copy_btn = QPushButton("Copy Error ID")
        copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self._info.error_id)
        )
        id_row.addWidget(id_label)
        id_row.addStretch(1)
        id_row.addWidget(copy_btn)
        layout.addLayout(id_row)

        if self._info.log_reference is not None:
            log_label = QLabel(f"Log file: {self._info.log_reference}")
            log_label.setObjectName("versionLabel")
            log_label.setWordWrap(True)
            layout.addWidget(log_label)

        self.details_toggle = QPushButton("Show Technical Details")
        self.details_toggle.setCheckable(True)
        self.details_toggle.toggled.connect(self._toggle_details)
        layout.addWidget(self.details_toggle)

        self.details_text = QPlainTextEdit()
        self.details_text.setPlainText(
            f"Code: {self._info.code}\n"
            f"Occurred at: {self._info.occurred_at.isoformat(timespec='seconds')}\n\n"
            f"{self._info.technical_detail}"
        )
        self.details_text.setReadOnly(True)
        self.details_text.setVisible(False)
        self.details_text.setMinimumHeight(160)
        layout.addWidget(self.details_text)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)

    def _toggle_details(self, checked: bool) -> None:
        self.details_text.setVisible(checked)
        self.details_toggle.setText(
            "Hide Technical Details" if checked else "Show Technical Details"
        )
        self.adjustSize()
