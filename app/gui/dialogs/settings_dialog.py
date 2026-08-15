"""Professional Settings dialog with tabbed sections.

Operates on a local *copy* of `ApplicationSettings` and only reports the
new settings back to the caller via `result_settings()` when the user
clicks OK/Apply, so cancelling never leaves partially-applied state.
"""
from __future__ import annotations

import copy

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.enums import ComparisonMode, ExportFormat, LogLevel, Theme
from app.core.models import ApplicationSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: ApplicationSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(460)
        self._settings = copy.deepcopy(settings)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_comparison_tab(), "Comparison")
        tabs.addTab(self._build_appearance_tab(), "Appearance")
        tabs.addTab(self._build_performance_tab(), "Performance")
        tabs.addTab(self._build_logging_tab(), "Logging")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_comparison_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.mode_combo = QComboBox()
        for mode in ComparisonMode:
            self.mode_combo.addItem(mode.display_name, mode)
        self.mode_combo.setCurrentIndex(
            list(ComparisonMode).index(self._settings.comparison_settings.mode)
        )
        form.addRow("Comparison mode:", self.mode_combo)

        self.case_sensitive_cb = QCheckBox("Case sensitive")
        self.case_sensitive_cb.setChecked(self._settings.comparison_settings.case_sensitive)
        form.addRow(self.case_sensitive_cb)

        self.ignore_leading_trailing_cb = QCheckBox("Ignore leading/trailing whitespace")
        self.ignore_leading_trailing_cb.setChecked(
            self._settings.comparison_settings.ignore_leading_trailing_whitespace
        )
        form.addRow(self.ignore_leading_trailing_cb)

        self.ignore_repeated_spaces_cb = QCheckBox("Ignore repeated spaces")
        self.ignore_repeated_spaces_cb.setChecked(
            self._settings.comparison_settings.ignore_repeated_spaces
        )
        form.addRow(self.ignore_repeated_spaces_cb)

        self.ignore_blank_lines_cb = QCheckBox("Ignore blank lines")
        self.ignore_blank_lines_cb.setChecked(
            self._settings.comparison_settings.ignore_blank_lines
        )
        form.addRow(self.ignore_blank_lines_cb)

        self.ignore_line_endings_cb = QCheckBox("Ignore line-ending differences (CRLF/LF/CR)")
        self.ignore_line_endings_cb.setChecked(
            self._settings.comparison_settings.ignore_line_ending_differences
        )
        form.addRow(self.ignore_line_endings_cb)

        self.normalize_unicode_cb = QCheckBox("Normalize Unicode (NFC) before comparing")
        self.normalize_unicode_cb.setChecked(self._settings.comparison_settings.normalize_unicode)
        form.addRow(self.normalize_unicode_cb)

        return widget

    def _build_appearance_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Light", Theme.LIGHT)
        self.theme_combo.addItem("Dark", Theme.DARK)
        self.theme_combo.setCurrentIndex(0 if self._settings.theme == Theme.LIGHT else 1)
        form.addRow("Theme:", self.theme_combo)

        self.font_family_edit = QLineEdit(self._settings.font_family)
        form.addRow("Font family:", self.font_family_edit)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(7, 24)
        self.font_size_spin.setValue(self._settings.font_size)
        form.addRow("Font size:", self.font_size_spin)

        self.export_format_combo = QComboBox()
        for fmt in ExportFormat:
            self.export_format_combo.addItem(fmt.value.upper(), fmt)
        self.export_format_combo.setCurrentIndex(
            list(ExportFormat).index(self._settings.default_export_format)
        )
        form.addRow("Default export format:", self.export_format_combo)

        return widget

    def _build_performance_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.worker_count_spin = QSpinBox()
        self.worker_count_spin.setRange(1, 16)
        self.worker_count_spin.setValue(self._settings.worker_thread_count)
        form.addRow("Worker threads:", self.worker_count_spin)

        self.large_file_spin = QSpinBox()
        self.large_file_spin.setRange(1, 2048)
        self.large_file_spin.setSuffix(" MB")
        self.large_file_spin.setValue(
            max(1, self._settings.large_file_threshold_bytes // (1024 * 1024))
        )
        form.addRow("Large-file threshold:", self.large_file_spin)

        note = QGroupBox("About background processing")
        note_layout = QVBoxLayout(note)
        from PySide6.QtWidgets import QLabel

        label = QLabel(
            "Comparisons always run on a background thread with progress "
            "reporting and cancellation support; the GUI never blocks."
        )
        label.setWordWrap(True)
        note_layout.addWidget(label)
        form.addRow(note)

        return widget

    def _build_logging_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.log_level_combo = QComboBox()
        for level in LogLevel:
            self.log_level_combo.addItem(level.value, level.value)
        self.log_level_combo.setCurrentText(self._settings.log_level)
        form.addRow("Log level:", self.log_level_combo)

        return widget

    # ------------------------------------------------------------------
    def result_settings(self) -> ApplicationSettings:
        from app.core.models import ComparisonSettings

        comparison_settings = ComparisonSettings(
            mode=self.mode_combo.currentData(),
            case_sensitive=self.case_sensitive_cb.isChecked(),
            ignore_leading_trailing_whitespace=self.ignore_leading_trailing_cb.isChecked(),
            ignore_repeated_spaces=self.ignore_repeated_spaces_cb.isChecked(),
            ignore_blank_lines=self.ignore_blank_lines_cb.isChecked(),
            ignore_line_ending_differences=self.ignore_line_endings_cb.isChecked(),
            normalize_unicode=self.normalize_unicode_cb.isChecked(),
        )
        return ApplicationSettings(
            theme=self.theme_combo.currentData(),
            font_family=self.font_family_edit.text() or ApplicationSettings().font_family,
            font_size=self.font_size_spin.value(),
            default_export_format=self.export_format_combo.currentData(),
            worker_thread_count=self.worker_count_spin.value(),
            large_file_threshold_bytes=self.large_file_spin.value() * 1024 * 1024,
            log_level=self.log_level_combo.currentData(),
            comparison_settings=comparison_settings,
        )
