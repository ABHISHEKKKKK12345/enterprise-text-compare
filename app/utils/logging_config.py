"""Logging setup.

Design notes:
- Three rotating log files: application (INFO+), error (WARNING+), debug
  (DEBUG+, only written when the configured level is DEBUG).
- Log rotation via `RotatingFileHandler` prevents unbounded disk growth.
- IMPORTANT (privacy): callers must never pass raw document content into
  log messages. Helper functions below (`safe_preview`) provide a
  redacted/length-limited preview for the rare cases where logging a
  fragment is genuinely useful for debugging.
"""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from app.core.constants import LOG_FILE_BACKUP_COUNT, LOG_FILE_MAX_BYTES

_CONFIGURED = False


def configure_logging(log_dir: Path, level: str = "INFO") -> None:
    global _CONFIGURED
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    if _CONFIGURED:
        # Allow reconfiguration (e.g. user changes log level in Settings)
        for handler in list(root.handlers):
            root.removeHandler(handler)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app_handler = logging.handlers.RotatingFileHandler(
        log_dir / "application.log",
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8",
    )
    app_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    app_handler.setFormatter(formatter)

    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)

    handlers = [app_handler, error_handler]

    if level.upper() == "DEBUG":
        debug_handler = logging.handlers.RotatingFileHandler(
            log_dir / "debug.log",
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUP_COUNT,
            encoding="utf-8",
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)
        handlers.append(debug_handler)

    for handler in handlers:
        root.addHandler(handler)

    _CONFIGURED = True
    logging.getLogger(__name__).info("Logging configured. Level=%s, dir=%s", level, log_dir)


def safe_preview(text: str, max_len: int = 40) -> str:
    """Return a short, length-limited preview safe for logs.

    Never logs full document content. Intended only for narrow debugging
    cases (e.g. confirming a file was non-empty); prefer logging
    lengths/counts instead of content wherever possible.
    """
    if text is None:
        return ""
    collapsed = text.replace("\n", "\\n")
    if len(collapsed) <= max_len:
        return collapsed
    return collapsed[:max_len] + "...(truncated)"
