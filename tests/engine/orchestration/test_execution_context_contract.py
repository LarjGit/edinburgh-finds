"""
Tests for ExecutionContext architectural contract (architecture.md 3.6).

Validates that ExecutionContext matches the architecture specification:
- Frozen dataclass (immutable)
- Required fields: lens_id, lens_contract, lens_hash
- No mutable state or business logic
"""

import pytest
from dataclasses import FrozenInstanceError
from types import MappingProxyType
from engine.orchestration.execution_context import ExecutionContext


class TestExecutionContextContract:
    """Test ExecutionContext matches docs/target-architecture.md 3.6 specification."""

    def test_execution_context_is_frozen_dataclass(self):
        """ExecutionContext must be a frozen dataclass per docs/target-architecture.md 3.6."""
        ctx = ExecutionContext(
            lens_id="edinburgh_finds",
            lens_contract={"test": "data"},
            lens_hash="abc123"
        )

        # Verify it's a dataclass
        assert hasattr(ctx, "__dataclass_fields__"), "ExecutionContext must be a dataclass"

        # Verify it's frozen (attempting to set attribute should raise FrozenInstanceError)
        with pytest.raises(FrozenInstanceError):
            ctx.lens_id = "modified"

    def test_execution_context_has_required_fields(self):
        """ExecutionContext must have lens_id, lens_contract, lens_hash fields."""
        ctx = ExecutionContext(
            lens_id="edinburgh_finds",
            lens_contract={"mapping_rules": []},
            lens_hash="def456"
        )

        assert ctx.lens_id == "edinburgh_finds"
        assert ctx.lens_contract == {"mapping_rules": []}
        assert ctx.lens_hash == "def456"

    def test_execution_context_lens_hash_optional(self):
        """lens_hash field must be Optional[str] per docs/target-architecture.md 3.6."""
        ctx = ExecutionContext(
            lens_id="edinburgh_finds",
            lens_contract={},
            lens_hash=None
        )

        assert ctx.lens_hash is None

    def test_execution_context_is_immutable(self):
        """ExecutionContext must be completely immutable (frozen)."""
        ctx = ExecutionContext(
            lens_id="test_lens",
            lens_contract={"test": "data"},
            lens_hash="hash123"
        )

        # Cannot modify lens_id
        with pytest.raises(FrozenInstanceError):
            ctx.lens_id = "modified"

        # Cannot modify lens_contract
        with pytest.raises(FrozenInstanceError):
            ctx.lens_contract = {}

        # Cannot modify lens_hash
        with pytest.raises(FrozenInstanceError):
            ctx.lens_hash = "modified"

    def test_execution_context_contains_only_serializable_data(self):
        """ExecutionContext must contain only plain serializable data."""
        ctx = ExecutionContext(
            lens_id="test_lens",
            lens_contract={"key": "value", "nested": {"data": 123}},
            lens_hash="hash456"
        )

        # All fields should be serializable types
        assert isinstance(ctx.lens_id, str)
        assert isinstance(ctx.lens_contract, dict)
        assert isinstance(ctx.lens_hash, (str, type(None)))

    def test_execution_context_has_no_mutable_state(self):
        """ExecutionContext must NOT contain mutable state (candidates, metrics, etc)."""
        ctx = ExecutionContext(
            lens_id="test",
            lens_contract={},
            lens_hash=None
        )

        # Should NOT have orchestrator state fields
        assert not hasattr(ctx, "candidates"), "ExecutionContext must not have 'candidates'"
        assert not hasattr(ctx, "accepted_entities"), "ExecutionContext must not have 'accepted_entities'"
        assert not hasattr(ctx, "metrics"), "ExecutionContext must not have 'metrics'"
        assert not hasattr(ctx, "errors"), "ExecutionContext must not have 'errors'"
        assert not hasattr(ctx, "budget_spent_usd"), "ExecutionContext must not have 'budget_spent_usd'"
        assert not hasattr(ctx, "confidence"), "ExecutionContext must not have 'confidence'"

    def test_execution_context_has_no_business_logic(self):
        """ExecutionContext must NOT contain business logic methods."""
        ctx = ExecutionContext(
            lens_id="test",
            lens_contract={},
            lens_hash=None
        )

        # Should NOT have business logic methods
        assert not hasattr(ctx, "accept_entity"), "ExecutionContext must not have accept_entity method"
        assert not hasattr(ctx, "_find_fuzzy_match"), "ExecutionContext must not have _find_fuzzy_match method"
        assert not hasattr(ctx, "_generate_entity_key"), "ExecutionContext must not have _generate_entity_key method"
