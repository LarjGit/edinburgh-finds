"""
Unit tests for Condition DSL evaluation.

Tests verify:
- Operator enum and basic conditions
- None-safe evaluation for all operators
- Nested path resolution
- CompositeCondition (AND, OR, NOT)
- ConditionParser for dict/YAML parsing
- build_eval_context helper
"""

import pytest
from engine.orchestration.conditions import (
    Operator,
    Condition,
    CompositeCondition,
    ConditionParser,
    build_eval_context,
)
from engine.orchestration.types import IngestRequest, IngestionMode
from engine.orchestration.query_features import QueryFeatures


class TestOperator:
    """Tests for Operator enum."""

    def test_has_comparison_operators(self):
        """Should have standard comparison operators."""
        assert Operator.EQ is not None
        assert Operator.NE is not None
        assert Operator.GT is not None
        assert Operator.LT is not None
        assert Operator.GTE is not None
        assert Operator.LTE is not None

    def test_has_collection_operators(self):
        """Should have collection operators."""
        assert Operator.CONTAINS is not None
        assert Operator.INTERSECTS is not None

    def test_has_logical_operators(self):
        """Should have logical operators."""
        assert Operator.AND is not None
        assert Operator.OR is not None
        assert Operator.NOT is not None


class TestCondition:
    """Tests for basic Condition evaluation."""

    def test_eq_operator_with_match(self):
        """EQ should return True when values match."""
        condition = Condition(field="mode", operator=Operator.EQ, value="resolve_one")
        context = {"mode": "resolve_one"}
        assert condition.evaluate(context) is True

    def test_eq_operator_with_no_match(self):
        """EQ should return False when values don't match."""
        condition = Condition(field="mode", operator=Operator.EQ, value="resolve_one")
        context = {"mode": "discover_many"}
        assert condition.evaluate(context) is False

    def test_ne_operator(self):
        """NE should return True when values differ."""
        condition = Condition(field="mode", operator=Operator.NE, value="resolve_one")
        context = {"mode": "discover_many"}
        assert condition.evaluate(context) is True

    def test_gt_operator(self):
        """GT should compare numbers correctly."""
        condition = Condition(field="count", operator=Operator.GT, value=10)
        assert condition.evaluate({"count": 15}) is True
        assert condition.evaluate({"count": 10}) is False
        assert condition.evaluate({"count": 5}) is False

    def test_lt_operator(self):
        """LT should compare numbers correctly."""
        condition = Condition(field="count", operator=Operator.LT, value=10)
        assert condition.evaluate({"count": 5}) is True
        assert condition.evaluate({"count": 10}) is False
        assert condition.evaluate({"count": 15}) is False

    def test_gte_operator(self):
        """GTE should handle equality and greater-than."""
        condition = Condition(field="confidence", operator=Operator.GTE, value=0.8)
        assert condition.evaluate({"confidence": 0.9}) is True
        assert condition.evaluate({"confidence": 0.8}) is True
        assert condition.evaluate({"confidence": 0.7}) is False

    def test_lte_operator(self):
        """LTE should handle equality and less-than."""
        condition = Condition(field="confidence", operator=Operator.LTE, value=0.8)
        assert condition.evaluate({"confidence": 0.7}) is True
        assert condition.evaluate({"confidence": 0.8}) is True
        assert condition.evaluate({"confidence": 0.9}) is False

    def test_contains_operator_with_string(self):
        """CONTAINS should check string containment."""
        condition = Condition(field="query", operator=Operator.CONTAINS, value="tennis")
        assert condition.evaluate({"query": "tennis courts"}) is True
        assert condition.evaluate({"query": "padel"}) is False

    def test_contains_operator_with_list(self):
        """CONTAINS should check list membership."""
        condition = Condition(field="tags", operator=Operator.CONTAINS, value="sports")
        assert condition.evaluate({"tags": ["sports", "outdoor"]}) is True
        assert condition.evaluate({"tags": ["indoor", "facility"]}) is False

    def test_intersects_operator(self):
        """INTERSECTS should check for any common elements."""
        condition = Condition(
            field="activities",
            operator=Operator.INTERSECTS,
            value=["tennis", "padel"],
        )
        assert condition.evaluate({"activities": ["tennis", "football"]}) is True
        assert condition.evaluate({"activities": ["football", "rugby"]}) is False
        assert condition.evaluate({"activities": []}) is False


class TestConditionNoneSafety:
    """Tests for None-safe behavior of all operators."""

    def test_eq_with_none_field(self):
        """EQ should return False when field is None."""
        condition = Condition(field="missing", operator=Operator.EQ, value="test")
        assert condition.evaluate({"other": "value"}) is False

    def test_eq_with_none_value_in_context(self):
        """EQ should handle None value in context."""
        condition = Condition(field="field", operator=Operator.EQ, value="test")
        assert condition.evaluate({"field": None}) is False

    def test_contains_with_none_field(self):
        """CONTAINS should return False when field is None."""
        condition = Condition(field="missing", operator=Operator.CONTAINS, value="test")
        assert condition.evaluate({}) is False

    def test_contains_with_none_value_in_context(self):
        """CONTAINS should return False when context value is None."""
        condition = Condition(field="field", operator=Operator.CONTAINS, value="test")
        assert condition.evaluate({"field": None}) is False

    def test_intersects_with_none_field(self):
        """INTERSECTS should return False when field is None."""
        condition = Condition(
            field="missing", operator=Operator.INTERSECTS, value=["a", "b"]
        )
        assert condition.evaluate({}) is False

    def test_intersects_with_none_value_in_context(self):
        """INTERSECTS should return False when context value is None."""
        condition = Condition(
            field="field", operator=Operator.INTERSECTS, value=["a", "b"]
        )
        assert condition.evaluate({"field": None}) is False

    def test_gt_with_none_field(self):
        """GT should return False when field is None."""
        condition = Condition(field="missing", operator=Operator.GT, value=10)
        assert condition.evaluate({}) is False

    def test_comparison_with_none_in_context(self):
        """Comparison operators should handle None gracefully."""
        condition = Condition(field="count", operator=Operator.GT, value=10)
        assert condition.evaluate({"count": None}) is False


class TestNestedPathResolution:
    """Tests for nested path resolution (e.g., request.mode, query_features.has_geo_intent)."""

    def test_resolve_simple_path(self):
        """Should resolve simple field paths."""
        condition = Condition(field="mode", operator=Operator.EQ, value="test")
        assert condition.evaluate({"mode": "test"}) is True

    def test_resolve_nested_path(self):
        """Should resolve nested paths with dot notation."""
        condition = Condition(
            field="request.mode", operator=Operator.EQ, value="resolve_one"
        )
        context = {"request": {"mode": "resolve_one"}}
        assert condition.evaluate(context) is True

    def test_resolve_deeply_nested_path(self):
        """Should resolve deeply nested paths."""
        condition = Condition(field="a.b.c", operator=Operator.EQ, value="deep")
        context = {"a": {"b": {"c": "deep"}}}
        assert condition.evaluate(context) is True

    def test_missing_nested_path_returns_none(self):
        """Should return None for missing nested paths."""
        condition = Condition(field="a.b.c", operator=Operator.EQ, value="test")
        context = {"a": {"x": "value"}}
        # Missing path should be treated as None, comparison returns False
        assert condition.evaluate(context) is False

    def test_partially_missing_nested_path(self):
        """Should handle partially missing nested paths."""
        condition = Condition(field="a.b.c", operator=Operator.EQ, value="test")
        context = {"a": None}
        assert condition.evaluate(context) is False


class TestCompositeCondition:
    """Tests for CompositeCondition (AND, OR, NOT)."""

    def test_and_operator_all_true(self):
        """AND should return True when all conditions are True."""
        cond1 = Condition(field="a", operator=Operator.EQ, value=1)
        cond2 = Condition(field="b", operator=Operator.EQ, value=2)
        composite = CompositeCondition(operator=Operator.AND, conditions=[cond1, cond2])
        assert composite.evaluate({"a": 1, "b": 2}) is True

    def test_and_operator_one_false(self):
        """AND should return False when any condition is False."""
        cond1 = Condition(field="a", operator=Operator.EQ, value=1)
        cond2 = Condition(field="b", operator=Operator.EQ, value=2)
        composite = CompositeCondition(operator=Operator.AND, conditions=[cond1, cond2])
        assert composite.evaluate({"a": 1, "b": 99}) is False

    def test_or_operator_one_true(self):
        """OR should return True when any condition is True."""
        cond1 = Condition(field="a", operator=Operator.EQ, value=1)
        cond2 = Condition(field="b", operator=Operator.EQ, value=2)
        composite = CompositeCondition(operator=Operator.OR, conditions=[cond1, cond2])
        assert composite.evaluate({"a": 1, "b": 99}) is True

    def test_or_operator_all_false(self):
        """OR should return False when all conditions are False."""
        cond1 = Condition(field="a", operator=Operator.EQ, value=1)
        cond2 = Condition(field="b", operator=Operator.EQ, value=2)
        composite = CompositeCondition(operator=Operator.OR, conditions=[cond1, cond2])
        assert composite.evaluate({"a": 99, "b": 99}) is False

    def test_not_operator(self):
        """NOT should invert condition result."""
        cond = Condition(field="a", operator=Operator.EQ, value=1)
        composite = CompositeCondition(operator=Operator.NOT, conditions=[cond])
        assert composite.evaluate({"a": 2}) is True
        assert composite.evaluate({"a": 1}) is False

    def test_nested_composite_conditions(self):
        """Should support nesting composite conditions."""
        # (a == 1 AND b == 2) OR (c == 3)
        and_cond = CompositeCondition(
            operator=Operator.AND,
            conditions=[
                Condition(field="a", operator=Operator.EQ, value=1),
                Condition(field="b", operator=Operator.EQ, value=2),
            ],
        )
        or_cond = CompositeCondition(
            operator=Operator.OR,
            conditions=[
                and_cond,
                Condition(field="c", operator=Operator.EQ, value=3),
            ],
        )
        assert or_cond.evaluate({"a": 1, "b": 2, "c": 99}) is True
        assert or_cond.evaluate({"a": 99, "b": 99, "c": 3}) is True
        assert or_cond.evaluate({"a": 99, "b": 99, "c": 99}) is False


class TestConditionParser:
    """Tests for parsing conditions from dict/YAML."""

    def test_parse_simple_condition(self):
        """Should parse simple condition from dict."""
        spec = {"field": "mode", "operator": "EQ", "value": "resolve_one"}
        condition = ConditionParser.parse(spec)
        assert isinstance(condition, Condition)
        assert condition.field == "mode"
        assert condition.operator == Operator.EQ
        assert condition.value == "resolve_one"

    def test_parse_composite_and(self):
        """Should parse AND composite condition."""
        spec = {
            "operator": "AND",
            "conditions": [
                {"field": "a", "operator": "EQ", "value": 1},
                {"field": "b", "operator": "EQ", "value": 2},
            ],
        }
        condition = ConditionParser.parse(spec)
        assert isinstance(condition, CompositeCondition)
        assert condition.operator == Operator.AND
        assert len(condition.conditions) == 2

    def test_parse_nested_composite(self):
        """Should parse nested composite conditions."""
        spec = {
            "operator": "OR",
            "conditions": [
                {
                    "operator": "AND",
                    "conditions": [
                        {"field": "a", "operator": "EQ", "value": 1},
                        {"field": "b", "operator": "EQ", "value": 2},
                    ],
                },
                {"field": "c", "operator": "EQ", "value": 3},
            ],
        }
        condition = ConditionParser.parse(spec)
        assert isinstance(condition, CompositeCondition)
        assert condition.operator == Operator.OR
        assert isinstance(condition.conditions[0], CompositeCondition)


class TestBuildEvalContext:
    """Tests for build_eval_context helper."""

    def test_build_context_includes_request_fields(self):
        """Context should include request.* fields."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            query="test",
            min_confidence=0.8,
        )
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=True,
        )
        context = build_eval_context(request, query_features, execution_context=None)

        # Should be able to access request fields via nested path
        assert "request" in context
        assert context["request"]["ingestion_mode"] == IngestionMode.RESOLVE_ONE
        assert context["request"]["min_confidence"] == 0.8

    def test_build_context_includes_query_features(self):
        """Context should include query_features.* fields."""
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY, query="test")
        query_features = QueryFeatures(
            looks_like_category_search=True,
            has_geo_intent=False,
        )
        context = build_eval_context(request, query_features, execution_context=None)

        assert "query_features" in context
        assert context["query_features"]["looks_like_category_search"] is True
        assert context["query_features"]["has_geo_intent"] is False

    def test_build_context_includes_precomputed_booleans(self):
        """Context should include precomputed boolean shortcuts."""
        request = IngestRequest(ingestion_mode=IngestionMode.RESOLVE_ONE, query="test")
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=True,
        )
        context = build_eval_context(request, query_features, execution_context=None)

        # Should have convenience booleans
        assert "is_resolve_one" in context
        assert context["is_resolve_one"] is True
        assert "is_discover_many" in context
        assert context["is_discover_many"] is False

    def test_build_context_includes_execution_context(self):
        """Context should include execution context when provided."""
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY, query="test")
        query_features = QueryFeatures(
            looks_like_category_search=True,
            has_geo_intent=False,
        )
        exec_context = {"candidates": [], "accepted_entities": []}
        context = build_eval_context(request, query_features, exec_context)

        assert "context" in context
        assert context["context"] == exec_context


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_comparison_with_incomparable_types(self):
        """Comparison operators should handle type errors gracefully."""
        condition = Condition(field="value", operator=Operator.GT, value=10)
        # Comparing string to number should return False, not raise
        assert condition.evaluate({"value": "string"}) is False

    def test_contains_with_incomparable_types(self):
        """CONTAINS should handle type errors gracefully."""
        condition = Condition(field="value", operator=Operator.CONTAINS, value="test")
        # Number is not iterable, should return False
        assert condition.evaluate({"value": 123}) is False

    def test_intersects_with_incomparable_types(self):
        """INTERSECTS should handle type errors gracefully."""
        condition = Condition(
            field="value", operator=Operator.INTERSECTS, value=["a", "b"]
        )
        # String can't be intersected as a set, should return False
        assert condition.evaluate({"value": "string"}) is False

    def test_composite_not_with_multiple_conditions_raises(self):
        """NOT operator should require exactly one condition."""
        cond1 = Condition(field="a", operator=Operator.EQ, value=1)
        cond2 = Condition(field="b", operator=Operator.EQ, value=2)
        composite = CompositeCondition(
            operator=Operator.NOT, conditions=[cond1, cond2]
        )
        with pytest.raises(ValueError, match="exactly one condition"):
            composite.evaluate({"a": 1, "b": 2})
