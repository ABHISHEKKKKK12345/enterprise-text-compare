"""Centralized constants. No magic numbers/strings elsewhere in the codebase."""
from __future__ import annotations

APPLICATION_NAME = "Enterprise Text Compare"
APPLICATION_ORG = "EnterpriseTextCompare"
APPLICATION_VERSION = "1.0.0"
APPLICATION_COPYRIGHT = "Copyright \u00a9 2026 Abhishek. All rights reserved."

# Files at or above this size (bytes) trigger a user-facing warning before
# a synchronous read is attempted, and always route comparison to a worker
# thread with chunked/streamed handling where possible.
DEFAULT_LARGE_FILE_THRESHOLD_BYTES = 10 * 1024 * 1024  # 10 MB

# Hard ceiling: files larger than this require explicit user confirmation.
DEFAULT_HUGE_FILE_WARNING_BYTES = 100 * 1024 * 1024  # 100 MB

# Supported "text-like" extensions. Anything else is treated as binary
# unless the user explicitly forces a text read.
SUPPORTED_TEXT_EXTENSIONS = {
    ".txt", ".log", ".csv", ".json", ".xml", ".html", ".htm", ".md",
    ".yaml", ".yml", ".py", ".java", ".js", ".ts", ".c", ".cpp", ".h",
    ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".sql", ".ini", ".cfg",
    ".conf", ".toml", ".sh", ".bat", ".ps1", ".properties", ".gradle",
    ".dockerfile", ".env",
}

# Candidate encodings tried, in order, during detection fallback.
FALLBACK_ENCODINGS = ["utf-8", "utf-8-sig", "utf-16", "cp1252", "latin-1"]

DEFAULT_WORKER_THREAD_COUNT = 2
DEFAULT_LOG_LEVEL = "INFO"
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024
LOG_FILE_BACKUP_COUNT = 5

DEFAULT_FONT_FAMILY = "Consolas, 'DejaVu Sans Mono', 'Courier New', monospace"
DEFAULT_FONT_SIZE = 10
MIN_FONT_SIZE = 7
MAX_FONT_SIZE = 24

CONFIG_FILE_NAME = "settings.json"
LOG_DIR_NAME = "logs"
CACHE_DIR_NAME = "cache"
