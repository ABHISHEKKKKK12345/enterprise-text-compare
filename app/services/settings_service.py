"""SettingsService — thin wrapper around `app.config.settings` so the GUI
depends on a service object (mockable/testable) rather than module-level
functions directly.
"""
from __future__ import annotations

import logging

from app.config.settings import get_cache_dir, get_config_dir, get_log_dir, load_settings, save_settings
from app.core.models import ApplicationSettings

logger = logging.getLogger(__name__)


class SettingsService:
    def __init__(self) -> None:
        self._settings: ApplicationSettings = load_settings()

    @property
    def current(self) -> ApplicationSettings:
        return self._settings

    def update(self, settings: ApplicationSettings) -> None:
        self._settings = settings
        save_settings(settings)
        logger.info("Application settings updated and persisted.")

    @staticmethod
    def config_dir():
        return get_config_dir()

    @staticmethod
    def log_dir():
        return get_log_dir()

    @staticmethod
    def cache_dir():
        return get_cache_dir()
