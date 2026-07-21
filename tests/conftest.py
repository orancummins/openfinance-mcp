"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from openfinance_mcp.config.settings import load_settings


@pytest.fixture(scope="session")
def settings():
    return load_settings()


@pytest.fixture()
def require_sandbox(settings):
    if not settings.configured:
        pytest.skip("No Finicity credentials resolved; skipping sandbox test.")
    return settings
