"""Shared test fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _dummy_xai_key(monkeypatch):
    """Provide a placeholder API key.

    The default ``xai:`` model string is resolved when an ``Agent`` is
    constructed, and the xAI provider expects ``XAI_API_KEY`` to be set. Tests
    never reach the network -- every run is overridden with ``TestModel`` or
    ``FunctionModel`` -- so a placeholder value is sufficient.
    """
    monkeypatch.setenv("XAI_API_KEY", "test-key-unused")
