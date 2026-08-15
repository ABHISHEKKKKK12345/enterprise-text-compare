"""Shared pytest fixtures.

Forces the Qt 'offscreen' platform plugin so the full GUI test suite can
run in CI / headless environments without a display server, and provides
a single shared `QApplication` instance (Qt does not support multiple
QApplication instances per process).
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="session")
def qapp():
    from app.application import create_application

    app = create_application()
    yield app
