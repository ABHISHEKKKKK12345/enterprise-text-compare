"""MainWindow — top-level application window.

Wires together the input panels, diff view, worker threads, services,
and dialogs. Contains orchestration/UI logic only; all actual comparison,
file I/O, and export logic lives in the service layer
(`app/services/*`) and comparison engine (`app/comparison/*`), which this
module treats as black boxes accessed only through their public APIs.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import APPLICATION_NAME, APPLICATION_VERSION
from app.core.enums import ExportFormat, Theme
from app.core.exceptions import ApplicationError
from app.core.models import ComparisonResult, SourceDocument
from app.gui.dialogs.about_dialog import AboutDialog
from app.gui.dialogs.error_dialog import ErrorDialog
from app.gui.dialogs.settings_dialog import SettingsDialog
from app.gui.styles.theme import get_stylesheet
from app.gui.widgets.diff_view import DiffView
from app.gui.widgets.source_panel import SourcePanel
from app.gui.workers.comparison_worker import ComparisonWorker
from app.gui.workers.file_load_worker import FileLoadWorker
from app.services.comparison_service import ComparisonService
from app.services.export_service import ExportService
from app.services.file_service import FileService
from app.services.settings_service import SettingsService
from app.utils.error_handler import build_error_information

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    # Dispatch signals for the persistent background workers (see
    # app/gui/workers/comparison_worker.py for why the workers/threads are
    # long-lived rather than created per-job). Connecting these to the
    # worker's `start` slot gives an automatic, safe, cross-thread QUEUED
    # connection: emitting the signal from the GUI thread posts the call
    # onto the already-running worker thread's event loop. Because a
    # QObject's slots run serially on its own thread, this also makes
    # overlapping jobs structurally impossible -- a second emit while a
    # job is in flight simply queues behind it, rather than racing it.
    compare_requested = Signal(object, object, object)  # source_a, source_b, settings
    file_load_requested = Signal(object, str, object, bool, int)

    def __init__(
        self,
        settings_service: SettingsService,
        comparison_service: Optional[ComparisonService] = None,
        export_service: Optional[ExportService] = None,
        file_service: Optional[FileService] = None,
    ) -> None:
        super().__init__()
        self._settings_service = settings_service
        self._comparison_service = comparison_service or ComparisonService()
        self._export_service = export_service or ExportService()
        self._file_service = file_service or FileService()

        self._source_a_doc: Optional[SourceDocument] = None
        self._source_b_doc: Optional[SourceDocument] = None
        self._last_result: Optional[ComparisonResult] = None

        self._pending_loads: list = []

        self.setWindowTitle(f"{APPLICATION_NAME} — Version {APPLICATION_VERSION}")
        self.resize(1280, 860)

        self._build_ui()
        self._init_background_workers()
        self._apply_theme(self._settings_service.current.theme)
        self._update_action_states()

    # ------------------------------------------------------------------
    # Persistent background workers
    # ------------------------------------------------------------------

    def _init_background_workers(self) -> None:
        """Create the long-lived comparison and file-load worker threads.

        Both threads are started once here and kept running for the
        application's lifetime; individual jobs are dispatched into them
        via queued signals (see the class-level Signal declarations
        above), never by creating/tearing down a QThread per job.
        """
        self._compare_thread = QThread(self)
        self._compare_thread.setObjectName("ComparisonWorkerThread")
        self._compare_worker = ComparisonWorker(self._comparison_service)
        self._compare_worker.moveToThread(self._compare_thread)
        self.compare_requested.connect(self._compare_worker.start)
        self._compare_worker.progress.connect(self.progress_bar.setValue)
        self._compare_worker.result_ready.connect(self._on_comparison_finished)
        self._compare_worker.cancelled.connect(self._on_comparison_cancelled)
        self._compare_worker.failed.connect(self._on_comparison_failed)
        self._compare_worker.finished.connect(self._on_comparison_worker_finished)
        self._compare_thread.start()

        self._load_thread = QThread(self)
        self._load_thread.setObjectName("FileLoadWorkerThread")
        self._load_worker = FileLoadWorker(self._comparison_service)
        self._load_worker.moveToThread(self._load_thread)
        self.file_load_requested.connect(self._load_worker.start)
        self._load_worker.result_ready.connect(self._on_file_load_result)
        self._load_worker.failed.connect(self._on_file_load_failure)
        self._load_worker.finished.connect(self._on_file_load_worker_finished)
        self._load_thread.start()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        root_layout.addLayout(self._build_header())

        splitter = QSplitter(Qt.Vertical)

        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        self.source_a_panel = SourcePanel("Source A")
        self.source_b_panel = SourcePanel("Source B")
        input_layout.addWidget(self.source_a_panel)
        input_layout.addWidget(self.source_b_panel)
        splitter.addWidget(input_widget)

        self.diff_view = DiffView()
        splitter.addWidget(self.diff_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root_layout.addWidget(splitter, 1)

        self.setCentralWidget(central)

        self._build_toolbar()
        self._build_status_bar()
        self._build_menu()
        self._wire_signals()

    def _build_header(self):
        header = QHBoxLayout()
        title = QLabel(APPLICATION_NAME)
        title.setObjectName("appTitle")
        version = QLabel(f"Version {APPLICATION_VERSION}")
        version.setObjectName("versionLabel")
        header.addWidget(title)
        header.addWidget(version)
        header.addStretch(1)
        self.help_button = QPushButton("Help / About")
        self.settings_header_button = QPushButton("Settings")
        header.addWidget(self.settings_header_button)
        header.addWidget(self.help_button)
        return header

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.compare_action = QAction("Compare", self)
        self.compare_action.setShortcut(QKeySequence("Ctrl+R"))
        self.compare_action.setObjectName("primaryButton")
        toolbar.addAction(self.compare_action)

        self.cancel_action = QAction("Cancel", self)
        self.cancel_action.setEnabled(False)
        toolbar.addAction(self.cancel_action)

        toolbar.addSeparator()

        self.settings_action = QAction("Settings", self)
        toolbar.addAction(self.settings_action)

        self.export_action = QAction("Export", self)
        self.export_action.setShortcut(QKeySequence("Ctrl+S"))
        self.export_action.setEnabled(False)
        toolbar.addAction(self.export_action)

        toolbar.addSeparator()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(220)
        self.progress_bar.setVisible(False)
        toolbar.addWidget(self.progress_bar)

    def _build_status_bar(self) -> None:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            "Select two files or enter text to begin comparison."
        )

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        # ---------------------------------------------------------- File
        file_menu = menu_bar.addMenu("&File")
        open_a_action = QAction("Open Source &A\u2026", self)
        open_a_action.setShortcut(QKeySequence("Ctrl+O"))
        open_a_action.triggered.connect(lambda: self._browse_and_load(self.source_a_panel, "Source A"))
        open_b_action = QAction("Open Source &B\u2026", self)
        open_b_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_b_action.triggered.connect(lambda: self._browse_and_load(self.source_b_panel, "Source B"))
        file_menu.addAction(open_a_action)
        file_menu.addAction(open_b_action)
        file_menu.addSeparator()
        save_a_action = QAction("&Save Source A As\u2026", self)
        save_a_action.triggered.connect(self.source_a_panel.trigger_save)
        save_b_action = QAction("Save Source &B As\u2026", self)
        save_b_action.triggered.connect(self.source_b_panel.trigger_save)
        file_menu.addAction(save_a_action)
        file_menu.addAction(save_b_action)
        file_menu.addSeparator()
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ---------------------------------------------------------- Edit
        edit_menu = menu_bar.addMenu("&Edit")

        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.undo_action.triggered.connect(lambda: self._dispatch_edit_op("undo"))
        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut(QKeySequence.Redo)
        self.redo_action.triggered.connect(lambda: self._dispatch_edit_op("redo"))
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()

        self.cut_action = QAction("Cu&t", self)
        self.cut_action.setShortcut(QKeySequence.Cut)
        self.cut_action.triggered.connect(lambda: self._dispatch_edit_op("cut"))
        self.copy_action = QAction("&Copy", self)
        self.copy_action.setShortcut(QKeySequence.Copy)
        self.copy_action.triggered.connect(lambda: self._dispatch_edit_op("copy"))
        self.paste_action = QAction("&Paste", self)
        self.paste_action.setShortcut(QKeySequence.Paste)
        self.paste_action.triggered.connect(lambda: self._dispatch_edit_op("paste"))
        self.select_all_action = QAction("Select &All", self)
        self.select_all_action.setShortcut(QKeySequence.SelectAll)
        self.select_all_action.triggered.connect(lambda: self._dispatch_edit_op("selectAll"))
        edit_menu.addAction(self.cut_action)
        edit_menu.addAction(self.copy_action)
        edit_menu.addAction(self.paste_action)
        edit_menu.addAction(self.select_all_action)
        edit_menu.addSeparator()

        find_action = QAction("&Find in Results\u2026", self)
        find_action.setShortcut(QKeySequence("Ctrl+F"))
        find_action.triggered.connect(self.diff_view.search_box.setFocus)
        edit_menu.addAction(find_action)

        # Edit actions target whichever editable widget currently has
        # focus (a source panel's QPlainTextEdit or the diff view's search
        # QLineEdit); their enabled state can only be evaluated at the
        # moment the menu is about to open, since it depends on focus and
        # editor content that changes continuously while the app is used.
        edit_menu.aboutToShow.connect(self._update_edit_menu_state)

        # ---------------------------------------------------------- View
        view_menu = menu_bar.addMenu("&View")

        self.zoom_in_action = QAction("Zoom &In", self)
        self.zoom_in_action.setShortcuts([QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")])
        self.zoom_in_action.triggered.connect(self.diff_view.zoom_in)
        self.zoom_out_action = QAction("Zoom &Out", self)
        self.zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
        self.zoom_out_action.triggered.connect(self.diff_view.zoom_out)
        self.reset_zoom_action = QAction("&Reset Zoom", self)
        self.reset_zoom_action.setShortcut(QKeySequence("Ctrl+0"))
        self.reset_zoom_action.triggered.connect(self.diff_view.reset_zoom)
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.reset_zoom_action)
        view_menu.addSeparator()

        self.light_theme_action = QAction("Light Theme", self, checkable=True)
        self.dark_theme_action = QAction("Dark Theme", self, checkable=True)
        view_menu.addAction(self.light_theme_action)
        view_menu.addAction(self.dark_theme_action)
        self.light_theme_action.triggered.connect(lambda: self._change_theme(Theme.LIGHT))
        self.dark_theme_action.triggered.connect(lambda: self._change_theme(Theme.DARK))

        # ---------------------------------------------------------- Compare
        compare_menu = menu_bar.addMenu("&Compare")
        # Reuse the SAME QAction objects as the toolbar so enabled state,
        # shortcuts, and behavior never diverge between the two surfaces.
        compare_menu.addAction(self.compare_action)
        compare_menu.addAction(self.cancel_action)
        compare_menu.addSeparator()

        self.first_diff_action = QAction("&First Difference", self)
        self.first_diff_action.setShortcut(QKeySequence("Ctrl+Home"))
        self.first_diff_action.triggered.connect(self.diff_view.go_to_first_difference)
        self.prev_diff_action = QAction("&Previous Difference", self)
        self.prev_diff_action.setShortcut(QKeySequence("Ctrl+Up"))
        self.prev_diff_action.triggered.connect(self.diff_view.go_to_previous_difference)
        self.next_diff_action = QAction("&Next Difference", self)
        self.next_diff_action.setShortcut(QKeySequence("Ctrl+Down"))
        self.next_diff_action.triggered.connect(self.diff_view.go_to_next_difference)
        self.last_diff_action = QAction("&Last Difference", self)
        self.last_diff_action.setShortcut(QKeySequence("Ctrl+End"))
        self.last_diff_action.triggered.connect(self.diff_view.go_to_last_difference)
        for action in (
            self.first_diff_action,
            self.prev_diff_action,
            self.next_diff_action,
            self.last_diff_action,
        ):
            compare_menu.addAction(action)
        compare_menu.addSeparator()
        compare_menu.addAction(self.settings_action)

        self.diff_view.difference_position_changed.connect(self._update_diff_nav_actions)
        self._update_diff_nav_actions(0, 0)

        # ---------------------------------------------------------- Help
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _wire_signals(self) -> None:
        self.source_a_panel.file_open_requested.connect(
            lambda path: self._load_file(self.source_a_panel, "Source A", path)
        )
        self.source_b_panel.file_open_requested.connect(
            lambda path: self._load_file(self.source_b_panel, "Source B", path)
        )
        self.source_a_panel.save_requested.connect(
            lambda text: self._save_source_text(text)
        )
        self.source_b_panel.save_requested.connect(
            lambda text: self._save_source_text(text)
        )
        self.source_a_panel.text_changed.connect(self._invalidate_last_result)
        self.source_b_panel.text_changed.connect(self._invalidate_last_result)

        self.compare_action.triggered.connect(self._start_comparison)
        self.cancel_action.triggered.connect(self._cancel_comparison)
        self.settings_action.triggered.connect(self._open_settings)
        self.settings_header_button.clicked.connect(self._open_settings)
        self.export_action.triggered.connect(self._export_result)
        self.help_button.clicked.connect(self._show_about)

        self.diff_view.difference_position_changed.connect(self._update_diff_status)

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _browse_and_load(self, panel: SourcePanel, label: str) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, f"Open {label}", "", "All Files (*)")
        if path_str:
            self._load_file(panel, label, Path(path_str))

    def _load_file(
        self,
        panel: SourcePanel,
        label: str,
        path: Path,
        *,
        force_encoding: Optional[str] = None,
        huge_file_confirmed: bool = False,
    ) -> None:
        threshold = self._settings_service.current.large_file_threshold_bytes
        panel.set_busy(True)
        self.status_bar.showMessage(f"Loading {path.name}\u2026")

        # The file-load worker is a single persistent, reusable worker
        # (see _init_background_workers): dispatching is just emitting a
        # queued signal, never creating a new QThread. If a load is
        # already in flight, Qt naturally queues this one to run right
        # after it on the same worker thread (no job is lost, and jobs
        # never run concurrently). _pending_loads tracks, in the same
        # FIFO order the worker will actually process them, which
        # panel/label/path each queued job belongs to, so results are
        # routed back to the correct panel.
        self._pending_loads.append((panel, label, path))
        self.file_load_requested.emit(path, label, force_encoding, huge_file_confirmed, threshold)

    def _on_file_load_result(self, document: SourceDocument) -> None:
        panel, _label, _path = self._pending_loads[0]
        self._on_file_loaded(panel, document)

    def _on_file_load_failure(self, info) -> None:
        panel, label, path = self._pending_loads[0]
        self._on_file_load_failed(panel, label, path, info)

    def _on_file_load_worker_finished(self) -> None:
        panel, _label, _path = self._pending_loads.pop(0)
        panel.set_busy(False)

    def _on_file_loaded(self, panel: SourcePanel, document: SourceDocument) -> None:
        panel.set_text(document.text)
        if document.file_metadata:
            panel.set_file_metadata(document.file_metadata)
        if panel is self.source_a_panel:
            self._source_a_doc = document
        else:
            self._source_b_doc = document
        self.status_bar.showMessage(f"Loaded {document.file_metadata.path.name}.", 5000)
        self._invalidate_last_result()
        self._update_action_states()

    def _on_file_load_failed(self, panel: SourcePanel, label: str, path: Path, info) -> None:
        if info.code == "ETC-FILE-TOOLARGE":
            reply = QMessageBox.question(
                self,
                "Large File",
                f"{info.user_message}\n\nProceed with loading '{path.name}' anyway? "
                "This may take a while.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._load_file(panel, label, path, huge_file_confirmed=True)
                return
            self.status_bar.showMessage("File load cancelled.", 5000)
            return
        self.status_bar.showMessage("Failed to load file.", 5000)
        ErrorDialog(info, self).exec()

    def _save_source_text(self, text: str) -> None:
        path_str, _ = QFileDialog.getSaveFileName(self, "Save Source As", "", "All Files (*)")
        if not path_str:
            return
        try:
            self._file_service.save_text(Path(path_str), text)
            self.status_bar.showMessage(f"Saved to {path_str}", 5000)
        except ApplicationError as exc:
            ErrorDialog(build_error_information(exc), self).exec()

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def _start_comparison(self) -> None:
        source_a = self._current_source(self.source_a_panel, "Source A", self._source_a_doc)
        source_b = self._current_source(self.source_b_panel, "Source B", self._source_b_doc)

        if source_a.is_empty and source_b.is_empty:
            self.status_bar.showMessage("Both sources are empty. Nothing to compare.", 5000)
            return

        settings = self._settings_service.current.comparison_settings

        self.compare_action.setEnabled(False)
        self.cancel_action.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Comparing\u2026")

        # Dispatch onto the persistent comparison worker thread (see
        # _init_background_workers). This is a queued cross-thread signal
        # emission, not thread creation, so there is no possibility of two
        # comparisons ever running concurrently: the worker's `start` slot
        # runs to completion, serially, on its own already-running thread
        # before it can process a second queued call.
        self.compare_requested.emit(source_a, source_b, settings)

    def _current_source(
        self, panel: SourcePanel, label: str, loaded_doc: Optional[SourceDocument]
    ) -> SourceDocument:
        text = panel.text()
        if loaded_doc is not None and loaded_doc.text == text:
            return loaded_doc
        return self._comparison_service.load_source_from_text(text, label)

    def _cancel_comparison(self) -> None:
        if self._compare_worker is not None:
            self._compare_worker.request_cancel()
            self.status_bar.showMessage("Cancelling\u2026")

    def _on_comparison_finished(self, result: ComparisonResult) -> None:
        self._last_result = result
        self.diff_view.load_result(result)
        stats = result.statistics
        if stats.is_identical:
            self.status_bar.showMessage("No differences found.", 8000)
        else:
            self.status_bar.showMessage(
                f"Comparison complete: {stats.total_differences} difference(s) found.", 8000
            )
        self._update_action_states()

    def _on_comparison_cancelled(self) -> None:
        self.status_bar.showMessage("Comparison cancelled.", 5000)

    def _on_comparison_failed(self, info) -> None:
        self.status_bar.showMessage("Comparison failed.", 5000)
        ErrorDialog(info, self).exec()

    def _on_comparison_worker_finished(self) -> None:
        # Fires once per comparison job (see ComparisonWorker.start), not
        # once per worker lifetime -- the worker and its thread persist
        # across many comparisons, so this only resets per-job UI state.
        self.compare_action.setEnabled(True)
        self.cancel_action.setEnabled(False)
        self.progress_bar.setVisible(False)

    def _invalidate_last_result(self) -> None:
        self._last_result = None
        self._update_action_states()

    # ------------------------------------------------------------------
    # Export / Settings / Theme
    # ------------------------------------------------------------------

    def _export_result(self) -> None:
        if self._last_result is None:
            QMessageBox.information(
                self, "Nothing to Export", "Run a comparison before exporting a report."
            )
            return

        default_fmt = self._settings_service.current.default_export_format
        filters = (
            "HTML Report (*.html);;Text Report (*.txt);;JSON Report (*.json);;"
            "CSV Report (*.csv);;Markdown Report (*.md)"
        )
        timestamp = self._last_result.generated_at.strftime("%Y%m%d_%H%M%S")
        default_name = f"comparison_report_{timestamp}.{default_fmt.value}"
        path_str, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Comparison Report",
            default_name,
            filters,
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not path_str:
            return

        destination = Path(path_str)
        if destination.exists():
            confirm = QMessageBox.question(
                self,
                "Overwrite File?",
                f"'{destination.name}' already exists. Do you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                self.status_bar.showMessage("Export cancelled.", 4000)
                return

        fmt_map = {
            "HTML Report (*.html)": ExportFormat.HTML,
            "Text Report (*.txt)": ExportFormat.TXT,
            "JSON Report (*.json)": ExportFormat.JSON,
            "CSV Report (*.csv)": ExportFormat.CSV,
            "Markdown Report (*.md)": ExportFormat.MARKDOWN,
        }
        fmt = fmt_map.get(selected_filter, default_fmt)

        try:
            self._export_service.export(self._last_result, destination, fmt)
            self.status_bar.showMessage(f"Report exported successfully to {destination}", 6000)
        except ApplicationError as exc:
            ErrorDialog(build_error_information(exc), self).exec()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._settings_service.current, self)
        if dialog.exec() == SettingsDialog.Accepted:
            new_settings = dialog.result_settings()
            try:
                self._settings_service.update(new_settings)
            except ApplicationError as exc:
                ErrorDialog(build_error_information(exc), self).exec()
                return
            self._apply_theme(new_settings.theme)
            self.diff_view.set_font_size(new_settings.font_size)
            self.diff_view.set_font_family(new_settings.font_family)
            self.status_bar.showMessage("Settings updated.", 4000)

    def _change_theme(self, theme: Theme) -> None:
        settings = self._settings_service.current
        settings.theme = theme
        try:
            self._settings_service.update(settings)
        except ApplicationError as exc:
            ErrorDialog(build_error_information(exc), self).exec()
            return
        self._apply_theme(theme)

    def _apply_theme(self, theme: Theme) -> None:
        app = self._qapp()
        if app is not None:
            app.setStyleSheet(get_stylesheet(theme))
        self.diff_view.apply_theme(theme)
        self.light_theme_action.setChecked(theme == Theme.LIGHT)
        self.dark_theme_action.setChecked(theme == Theme.DARK)

    def _qapp(self):
        from PySide6.QtWidgets import QApplication

        return QApplication.instance()

    def _show_about(self) -> None:
        AboutDialog(self).exec()

    # ------------------------------------------------------------------
    # Edit menu: dispatch to whichever editable widget currently has focus
    # ------------------------------------------------------------------

    def _focused_editable_widget(self):
        """Return the currently focused widget if it supports standard
        text-editing operations (QPlainTextEdit in a source panel, or the
        diff view's search QLineEdit), else None. The read-only diff
        results table is never a valid target."""
        widget = QApplication.focusWidget()
        if widget is None:
            return None
        if hasattr(widget, "undo") and hasattr(widget, "selectAll"):
            return widget
        return None

    def _dispatch_edit_op(self, op_name: str) -> None:
        widget = self._focused_editable_widget()
        if widget is None:
            return
        getattr(widget, op_name)()

    def _update_edit_menu_state(self) -> None:
        widget = self._focused_editable_widget()
        editable = widget is not None and not getattr(widget, "isReadOnly", lambda: False)()

        can_undo = editable and self._widget_can_undo(widget)
        can_redo = editable and self._widget_can_redo(widget)
        has_selection = editable and self._widget_has_selection(widget)
        can_paste = editable and QApplication.clipboard().text() != ""

        self.undo_action.setEnabled(can_undo)
        self.redo_action.setEnabled(can_redo)
        self.cut_action.setEnabled(has_selection)
        self.copy_action.setEnabled(has_selection)
        self.paste_action.setEnabled(can_paste)
        self.select_all_action.setEnabled(widget is not None)

    @staticmethod
    def _widget_can_undo(widget) -> bool:
        # QLineEdit exposes isUndoAvailable() directly; QPlainTextEdit/
        # QTextEdit only expose it on their underlying QTextDocument.
        if hasattr(widget, "isUndoAvailable"):
            return bool(widget.isUndoAvailable())
        if hasattr(widget, "document"):
            return bool(widget.document().isUndoAvailable())
        return False

    @staticmethod
    def _widget_can_redo(widget) -> bool:
        if hasattr(widget, "isRedoAvailable"):
            return bool(widget.isRedoAvailable())
        if hasattr(widget, "document"):
            return bool(widget.document().isRedoAvailable())
        return False

    @staticmethod
    def _widget_has_selection(widget) -> bool:
        # QLineEdit exposes hasSelectedText(); QPlainTextEdit/QTextEdit
        # expose selection state via their text cursor instead.
        if hasattr(widget, "hasSelectedText"):
            return bool(widget.hasSelectedText())
        if hasattr(widget, "textCursor"):
            return bool(widget.textCursor().hasSelection())
        return False

    # ------------------------------------------------------------------
    # Compare menu: difference navigation action states
    # ------------------------------------------------------------------

    def _update_diff_nav_actions(self, current: int, total: int) -> None:
        has_diffs = total > 0
        for action in (
            self.first_diff_action,
            self.prev_diff_action,
            self.next_diff_action,
            self.last_diff_action,
        ):
            action.setEnabled(has_diffs)

    # ------------------------------------------------------------------
    def _update_diff_status(self, current: int, total: int) -> None:
        if total:
            self.status_bar.showMessage(f"Difference {current} of {total}", 3000)

    def _update_action_states(self) -> None:
        self.export_action.setEnabled(self._last_result is not None)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # Ensure no background QThread is still executing when the process
        # exits: destroying/GC'ing a running QThread (or letting the Python
        # interpreter tear down while one is alive) can abort the process.
        # request_cancel() is cooperative (the engine polls it periodically,
        # see ComparisonEngine._PROGRESS_REPORT_STRIDE), so give it a
        # generous timeout rather than abandoning the wait after a short,
        # arbitrary window.
        if self._compare_worker is not None:
            self._compare_worker.request_cancel()
        self._wait_for_thread(self._compare_thread, "comparison")
        self._wait_for_thread(self._load_thread, "file load")

        logger.info("Application closing.")
        super().closeEvent(event)

    @staticmethod
    def _wait_for_thread(thread: Optional[QThread], label: str, timeout_ms: int = 5000) -> None:
        if thread is None:
            return
        try:
            if not thread.isRunning():
                return
        except RuntimeError:
            # The underlying C++ QThread object was already deleted (it
            # finished and was cleaned up via deleteLater()) between the
            # None-check above and this call. Nothing left to wait for.
            return
        thread.quit()
        if not thread.wait(timeout_ms):
            # Cooperative cancellation (ComparisonEngine polls a cancel flag
            # between rows) can't interrupt the line-alignment step itself
            # (a single difflib.SequenceMatcher call — see
            # app/comparison/line_diff.py) on very large/very different
            # inputs. Forcibly terminating a thread here (QThread.terminate())
            # was evaluated and rejected: it is non-deterministic against a
            # GIL-bound pure-Python loop with no safe cancellation point and
            # can itself hang indefinitely rather than freeing the thread.
            # Logging and allowing Qt's own event loop (still running via
            # app.exec()) to continue managing the thread in the background
            # is the safe choice; the thread will exit on its own once the
            # in-flight alignment/row-loop reaches its next cancellation
            # check.
            logger.warning(
                "%s background thread did not stop within %dms during shutdown; "
                "it will continue running in the background until its current "
                "operation reaches its next cancellation check.",
                label,
                timeout_ms,
            )
