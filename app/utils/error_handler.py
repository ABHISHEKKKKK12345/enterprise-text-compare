"""Centralized error handling.

Converts any exception (expected `ApplicationError` subclasses or truly
unexpected ones) into an `ErrorInformation` record: a short, user-safe
message plus a unique error ID that ties the on-screen dialog to the full
technical detail recorded in the log file. This is installed as Qt's/
Python's global excepthook so the application never crashes to a bare
traceback in front of the user.
"""
from __future__ import annotations

import logging
import sys
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.exceptions import ApplicationError
from app.core.models import ErrorInformation

logger = logging.getLogger(__name__)


def _generate_error_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:5].upper()
    return f"ETC-{stamp}-{suffix}"


def build_error_information(
    exc: BaseException, *, log_reference: Optional[Path] = None
) -> ErrorInformation:
    error_id = _generate_error_id()

    if isinstance(exc, ApplicationError):
        user_message = exc.user_message
        code = exc.code
        technical_detail = exc.technical_detail or "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
    else:
        user_message = (
            "An unexpected error occurred. The application will remain open; "
            "please check the technical details or application log if the "
            "problem persists."
        )
        code = "ETC-UNEXPECTED"
        technical_detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    info = ErrorInformation(
        error_id=error_id,
        code=code,
        user_message=user_message,
        technical_detail=technical_detail,
        occurred_at=datetime.now(),
        log_reference=log_reference,
    )

    logger.error(
        "[%s] code=%s message=%s\n%s",
        info.error_id,
        info.code,
        info.user_message,
        info.technical_detail,
    )
    return info


def install_global_excepthook(handler_callback) -> None:
    """Install a process-wide excepthook.

    `handler_callback(ErrorInformation)` is invoked for any exception that
    escapes normal handling, so the GUI can show a friendly dialog instead
    of the process crashing silently (or with a raw traceback on stderr
    that the end user never sees, effectively looking like a freeze/crash).
    """

    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        info = build_error_information(exc_value)
        try:
            handler_callback(info)
        except Exception:  # noqa: BLE001 - last resort, must not raise further
            logger.critical("Error handler callback itself failed.", exc_info=True)

    sys.excepthook = _hook
