"""FileService — save-to-disk operations for source panel content.

Distinct from `ExportService` (which renders comparison *results*): this
handles the simpler "Save Source A/B content as..." action from the input
panels.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.io.file_writer import write_text_atomic

logger = logging.getLogger(__name__)


class FileService:
    def save_text(self, path: Path, content: str) -> None:
        write_text_atomic(path, content)
        logger.info("Saved source content to %s", path)
