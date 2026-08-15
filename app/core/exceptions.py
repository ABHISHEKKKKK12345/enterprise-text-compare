"""Application-specific exception hierarchy.

Every exception carries a short machine-friendly `code` and a
`user_message` that is safe to display verbatim in the GUI (no
tracebacks, no internal paths, no sensitive content). Technical details
(the original exception, if any) are preserved separately so they can be
shown behind an expandable "Technical details" section and written to the
log, without ever being forced onto the user by default.
"""
from __future__ import annotations

from typing import Optional


class ApplicationError(Exception):
    """Base class for all handled application errors."""

    code: str = "ETC-GENERIC"

    def __init__(
        self,
        user_message: str,
        *,
        technical_detail: Optional[str] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.technical_detail = technical_detail or (str(cause) if cause else "")
        self.__cause__ = cause


class FileAccessError(ApplicationError):
    code = "ETC-FILE-ACCESS"


class FileNotFoundInAppError(ApplicationError):
    code = "ETC-FILE-NOTFOUND"


class PermissionDeniedError(ApplicationError):
    code = "ETC-FILE-PERM"


class UnsupportedFileTypeError(ApplicationError):
    code = "ETC-FILE-UNSUPPORTED"


class EncodingDetectionError(ApplicationError):
    code = "ETC-ENCODING"


class FileTooLargeError(ApplicationError):
    code = "ETC-FILE-TOOLARGE"


class InvalidComparisonInputError(ApplicationError):
    code = "ETC-INPUT-INVALID"


class ComparisonCancelledError(ApplicationError):
    code = "ETC-CANCELLED"


class ExportError(ApplicationError):
    code = "ETC-EXPORT"


class SettingsPersistenceError(ApplicationError):
    code = "ETC-SETTINGS"


class ComparisonEngineError(ApplicationError):
    code = "ETC-ENGINE"
