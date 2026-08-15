#!/usr/bin/env python3
"""Convenience launcher: `python run.py`.

Equivalent to `python -m app.main`, provided at the project root because
that's the first thing most users try to run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.application import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run())
