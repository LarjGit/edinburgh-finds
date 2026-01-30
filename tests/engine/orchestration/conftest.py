"""
Test fixtures for orchestration tests.

Provides common test infrastructure including lens configuration defaults.
"""
import pytest


@pytest.fixture(autouse=True)
def set_default_lens_id(monkeypatch):
    """
    Automatically set LENS_ID environment variable for all orchestration tests.

    After Mini-plan 2, orchestrate() requires a lens to be specified via either:
    - request.lens parameter, or
    - LENS_ID environment variable

    This fixture provides a sensible default (edinburgh_finds) for all tests,
    preventing lens_resolution errors in tests that don't care about lens behavior.

    Tests that explicitly validate missing-lens behavior should delete the env var:
        monkeypatch.delenv("LENS_ID", raising=False)
    """
    monkeypatch.setenv("LENS_ID", "edinburgh_finds")
