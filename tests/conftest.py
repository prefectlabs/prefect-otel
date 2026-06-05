"""Shared pytest fixtures for prefect-otel."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def clear_prefect_otel_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear integration settings between tests."""
    for key in list(os.environ):
        if key.startswith("PREFECT_INTEGRATIONS_OTEL_"):
            monkeypatch.delenv(key, raising=False)
    yield
