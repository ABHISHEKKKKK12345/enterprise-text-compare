"""Application bootstrap.

Responsible for: configuring logging, enabling High-DPI support,
installing the global exception handler, constructing the `QApplication`
and `MainWindow`, and applying the persisted theme at startup. Kept
separate from `main.py` so the application can be constructed
programmatically (e.g. from tests) without necessarily calling
`sys.exit`.
"""
from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from app.core.constants import APPLICATION_NAME, APPLICATION_ORG, APPLICATION_VERSION
from app.gui.dialogs.error_dialog import ErrorDialog
from app.gui.main_window import MainWindow
from app.gui.styles.theme import get_stylesheet
from app.services.settings_service import SettingsService
from app.utils import error_handler
from app.utils.logging_config import configure_logging

logger = logging.getLogger(__name__)


def _install_excepthook(app: QApplication) -> None:
    def handle(info) -> None:
        # Guard against a broken/closing app instance during shutdown.
        try:
            dialog = ErrorDialog(info)
            dialog.exec()
        except Exception:  # noqa: BLE001 - absolute last resort
            logger.critical("Failed to display error dialog for %s", info.error_id)

    error_handler.install_global_excepthook(handle)


def create_application() -> QApplication:
    # High-DPI scaling is automatic in Qt 6 (PySide6 6.x); AA_EnableHighDpiScaling
    # and AA_UseHighDpiPixmaps are deprecated no-ops kept only for very old Qt 6
    # point releases, so they are intentionally NOT set here to avoid deprecation
    # warnings on modern PySide6. High-DPI pixmaps remain enabled by default.
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APPLICATION_NAME)
    app.setOrganizationName(APPLICATION_ORG)
    app.setApplicationVersion(APPLICATION_VERSION)
    return app


def run() -> int:
    settings_service = SettingsService()

    configure_logging(SettingsService.log_dir(), level=settings_service.current.log_level)
    logger.info("Starting %s v%s", APPLICATION_NAME, APPLICATION_VERSION)

    app = create_application()
    _install_excepthook(app)
    app.setStyleSheet(get_stylesheet(settings_service.current.theme))

    window = MainWindow(settings_service)
    window.diff_view.set_font_size(settings_service.current.font_size)
    window.diff_view.set_font_family(settings_service.current.font_family)
    window.show()

    exit_code = app.exec()
    logger.info("Application shutdown. Exit code=%d", exit_code)
    return exit_code
