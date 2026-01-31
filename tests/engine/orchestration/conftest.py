"""
Test fixtures for orchestration tests.

Provides common test infrastructure including lens configuration defaults.
"""
import pytest
from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.orchestrator_state import OrchestratorState


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


@pytest.fixture
def mock_context():
    """
    Create mock ExecutionContext for tests (EC-001b).

    Per architecture.md 3.6: ExecutionContext is immutable and contains only lens contract.
    For mutable state (candidates, errors, metrics), use mock_state fixture instead.
    """
    return ExecutionContext(
        lens_id="test",
        lens_contract={
            "mapping_rules": [],
            "module_triggers": [],
            "modules": {},
            "facets": {},
            "values": [],
            "confidence_threshold": 0.7,
        }
    )


@pytest.fixture
def mock_state():
    """
    Create OrchestratorState for tests (EC-001b).

    Per architecture.md 3.6: OrchestratorState holds mutable execution state
    (candidates, accepted_entities, errors, metrics).
    """
    return OrchestratorState()
