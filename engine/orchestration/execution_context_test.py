"""
Unit tests for ExecutionContext.

Tests verify:
- Proper initialization of all storage containers
- Correct types for each container
- Mutable state management (lists, sets, dicts)
"""

import pytest
from engine.orchestration.execution_context import ExecutionContext


class TestExecutionContextStructure:
    """Tests for ExecutionContext structure and initialization."""

    def test_initialization_creates_empty_containers(self):
        """ExecutionContext should initialize with empty containers."""
        context = ExecutionContext()

        assert context.candidates == []
        assert context.accepted_entities == []
        assert context.accepted_entity_keys == set()
        assert context.evidence == {}
        assert context.seeds == {}

    def test_candidates_is_list(self):
        """candidates should be a list."""
        context = ExecutionContext()
        assert isinstance(context.candidates, list)

    def test_accepted_entities_is_list(self):
        """accepted_entities should be a list."""
        context = ExecutionContext()
        assert isinstance(context.accepted_entities, list)

    def test_accepted_entity_keys_is_set(self):
        """accepted_entity_keys should be a set."""
        context = ExecutionContext()
        assert isinstance(context.accepted_entity_keys, set)

    def test_evidence_is_dict(self):
        """evidence should be a dict."""
        context = ExecutionContext()
        assert isinstance(context.evidence, dict)

    def test_seeds_is_dict(self):
        """seeds should be a dict."""
        context = ExecutionContext()
        assert isinstance(context.seeds, dict)

    def test_containers_are_mutable(self):
        """All containers should be mutable (allow additions)."""
        context = ExecutionContext()

        # Should be able to modify lists
        context.candidates.append("test_candidate")
        assert len(context.candidates) == 1

        context.accepted_entities.append("test_entity")
        assert len(context.accepted_entities) == 1

        # Should be able to modify set
        context.accepted_entity_keys.add("test_key")
        assert len(context.accepted_entity_keys) == 1

        # Should be able to modify dicts
        context.evidence["test"] = "value"
        assert context.evidence["test"] == "value"

        context.seeds["test"] = "seed_value"
        assert context.seeds["test"] == "seed_value"

    def test_multiple_contexts_are_independent(self):
        """Multiple ExecutionContext instances should be independent."""
        context1 = ExecutionContext()
        context2 = ExecutionContext()

        context1.candidates.append("candidate1")
        context2.candidates.append("candidate2")

        assert len(context1.candidates) == 1
        assert len(context2.candidates) == 1
        assert context1.candidates[0] == "candidate1"
        assert context2.candidates[0] == "candidate2"
