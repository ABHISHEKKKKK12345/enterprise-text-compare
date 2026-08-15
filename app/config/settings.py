"""Platform-appropriate application directories and settings persistence.

Uses Qt's `QStandardPaths` so we automatically get the correct, idiomatic
location on Windows (`%APPDATA%`), Linux (XDG base dirs, e.g.
`~/.local/share`, `~/.config`, `~/.cache`), and macOS
(`~/Library/Application Support`, `~/Library/Caches`) without any
platform-specific branching in application code.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from PySide6.QtCore import QStandardPaths

from app.core.constants import CACHE_DIR_NAME, CONFIG_FILE_NAME, LOG_DIR_NAME
from app.core.enums import ComparisonMode, ExportFormat, Theme
from app.core.exceptions import SettingsPersistenceError
from app.core.models import ApplicationSettings, ComparisonSettings

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
    path = Path(base) if base else Path.home() / ".enterprise_text_compare" / "config"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_log_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    root = Path(base) if base else Path.home() / ".enterprise_text_compare"
    path = root / LOG_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
    path = Path(base) / CACHE_DIR_NAME if base else Path.home() / ".enterprise_text_compare" / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _settings_path() -> Path:
    return get_config_dir() / CONFIG_FILE_NAME


def _to_dict(settings: ApplicationSettings) -> Dict[str, Any]:
    data = asdict(settings)
    data["theme"] = settings.theme.value
    data["default_export_format"] = settings.default_export_format.value
    return data


def _from_dict(data: Dict[str, Any]) -> ApplicationSettings:
    comparison_data = data.get("comparison_settings", {}) or {}
    try:
        mode = ComparisonMode(comparison_data.get("mode", ComparisonMode.LINE.value))
    except ValueError:
        mode = ComparisonMode.LINE
    comparison_settings = ComparisonSettings(
        mode=mode,
        case_sensitive=comparison_data.get("case_sensitive", True),
        ignore_leading_trailing_whitespace=comparison_data.get(
            "ignore_leading_trailing_whitespace", False
        ),
        ignore_repeated_spaces=comparison_data.get("ignore_repeated_spaces", False),
        ignore_blank_lines=comparison_data.get("ignore_blank_lines", False),
        ignore_line_ending_differences=comparison_data.get(
            "ignore_line_ending_differences", True
        ),
        normalize_unicode=comparison_data.get("normalize_unicode", False),
        context_lines=comparison_data.get("context_lines", 3),
    )
    return ApplicationSettings(
        theme=Theme(data.get("theme", Theme.LIGHT.value)),
        font_family=data.get("font_family", ApplicationSettings().font_family),
        font_size=data.get("font_size", ApplicationSettings().font_size),
        default_export_format=ExportFormat(
            data.get("default_export_format", ExportFormat.HTML.value)
        ),
        worker_thread_count=data.get("worker_thread_count", 2),
        large_file_threshold_bytes=data.get(
            "large_file_threshold_bytes", ApplicationSettings().large_file_threshold_bytes
        ),
        log_level=data.get("log_level", "INFO"),
        comparison_settings=comparison_settings,
    )


def load_settings() -> ApplicationSettings:
    """Load persisted settings, falling back to defaults on any problem.

    Deliberately never raises: a corrupted or missing settings file must
    never prevent the application from starting.
    """
    path = _settings_path()
    if not path.exists():
        return ApplicationSettings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return _from_dict(raw)
    except Exception:  # noqa: BLE001 - intentional: never fail startup
        logger.warning("Failed to load settings from %s; using defaults.", path, exc_info=True)
        return ApplicationSettings()


def save_settings(settings: ApplicationSettings) -> None:
    path = _settings_path()
    try:
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(_to_dict(settings), indent=2), encoding="utf-8")
        tmp_path.replace(path)
    except OSError as exc:
        raise SettingsPersistenceError(
            "Unable to save application settings. Your preferences may not persist "
            "after restarting the application.",
            cause=exc,
        ) from exc
