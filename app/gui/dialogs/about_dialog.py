"""About / Help dialog."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from app.core.constants import APPLICATION_COPYRIGHT, APPLICATION_NAME, APPLICATION_VERSION


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APPLICATION_NAME}")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)

        title = QLabel(APPLICATION_NAME)
        title.setObjectName("appTitle")
        layout.addWidget(title)

        version = QLabel(f"Version {APPLICATION_VERSION}")
        version.setObjectName("versionLabel")
        layout.addWidget(version)

        copyright_label = QLabel(APPLICATION_COPYRIGHT)
        copyright_label.setObjectName("versionLabel")
        layout.addWidget(copyright_label)

        body = QLabel(
            "A local-first, enterprise-grade text comparison tool.\n\n"
            "Documents are compared entirely on this machine — no content "
            "is transmitted anywhere.\n\n"
            "Keyboard shortcuts:\n"
            "  Ctrl+O   Open Source A\n"
            "  Ctrl+Shift+O   Open Source B\n"
            "  Ctrl+R   Compare\n"
            "  Ctrl+S   Export\n"
            "  Ctrl+F   Search results\n"
            "  F3 / Shift+F3   Next / previous match\n"
            "  Ctrl+Q   Exit"
        )
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(body)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
