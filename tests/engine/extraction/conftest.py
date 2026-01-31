"""
Shared test fixtures for extraction tests.
"""

import pytest
from engine.orchestration.execution_context import ExecutionContext


@pytest.fixture
def mock_ctx():
    """
    Provides a minimal ExecutionContext for testing extractors.

    This fixture allows tests to call extractor.extract(raw_data, ctx=mock_ctx)
    without requiring full lens contract setup.
    """
    return ExecutionContext(
        lens_id="test_lens",
        lens_contract={
            "facets": {},
            "values": [],
            "mapping_rules": [],
            "modules": {},
            "module_triggers": []
        },
        lens_hash="test_hash"
    )
