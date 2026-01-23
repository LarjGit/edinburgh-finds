"""
Condition DSL for orchestration system.

Provides a safe, None-tolerant condition evaluation system for determining
connector eligibility and orchestration decisions. The DSL supports:

- Basic comparison operators (EQ, NE, GT, LT, GTE, LTE)
- Collection operators (CONTAINS, INTERSECTS)
- Logical operators (AND, OR, NOT)
- Nested path resolution (e.g., request.mode, query_features.has_geo_intent)
- None-safe evaluation (missing paths return None, operators handle gracefully)

All operators are None-safe: if a field is missing or None, comparison
operators return False instead of raising exceptions.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from engine.orchestration.types import IngestRequest
    from engine.orchestration.query_features import QueryFeatures


class Operator(Enum):
    """
    Operators supported by the condition DSL.

    Comparison operators: EQ, NE, GT, LT, GTE, LTE
    Collection operators: CONTAINS, INTERSECTS
    Logical operators: AND, OR, NOT
    """

    # Comparison operators
    EQ = "EQ"  # Equal
    NE = "NE"  # Not equal
    GT = "GT"  # Greater than
    LT = "LT"  # Less than
    GTE = "GTE"  # Greater than or equal
    LTE = "LTE"  # Less than or equal

    # Collection operators
    CONTAINS = "CONTAINS"  # String contains or list membership
    INTERSECTS = "INTERSECTS"  # List intersection (any common elements)

    # Logical operators
    AND = "AND"  # All conditions must be true
    OR = "OR"  # At least one condition must be true
    NOT = "NOT"  # Invert condition result


@dataclass
class Condition:
    """
    Basic condition for evaluating a single field against a value.

    Supports nested path resolution using dot notation (e.g., "request.mode",
    "query_features.has_geo_intent"). Missing paths are treated as None, and
    all operators handle None values gracefully by returning False.

    Attributes:
        field: Field path to evaluate (supports dot notation for nesting)
        operator: Comparison or collection operator
        value: Expected value to compare against
    """

    field: str
    operator: Operator
    value: Any

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate this condition against the provided context.

        Args:
            context: Evaluation context containing request, query_features, etc.

        Returns:
            Boolean result of the condition evaluation
        """
        # Resolve field value from context (supports nested paths)
        field_value = self._resolve_path(context, self.field)

        # Apply operator (all operators are None-safe)
        return self._apply_operator(field_value, self.operator, self.value)

    @staticmethod
    def _resolve_path(context: Dict[str, Any], path: str) -> Any:
        """
        Resolve a potentially nested path in the context.

        Supports dot notation (e.g., "request.mode" resolves to
        context["request"]["mode"]). Returns None if any part of
        the path is missing.

        Args:
            context: The context dictionary
            path: Field path (may contain dots for nesting)

        Returns:
            The value at the path, or None if not found
        """
        parts = path.split(".")
        current = context

        for part in parts:
            if not isinstance(current, dict):
                return None
            if part not in current:
                return None
            current = current[part]

        return current

    @staticmethod
    def _apply_operator(field_value: Any, operator: Operator, expected: Any) -> bool:
        """
        Apply an operator to compare field value against expected value.

        All operators are None-safe: if field_value is None, comparison
        operators return False instead of raising exceptions.

        Args:
            field_value: The actual value from the context
            operator: The operator to apply
            expected: The expected value to compare against

        Returns:
            Boolean result of the operation
        """
        # None-safety: if field is missing/None, most comparisons return False
        if operator == Operator.EQ:
            return field_value == expected if field_value is not None else False

        if operator == Operator.NE:
            return field_value != expected if field_value is not None else False

        if operator == Operator.GT:
            try:
                return field_value > expected if field_value is not None else False
            except TypeError:
                return False

        if operator == Operator.LT:
            try:
                return field_value < expected if field_value is not None else False
            except TypeError:
                return False

        if operator == Operator.GTE:
            try:
                return field_value >= expected if field_value is not None else False
            except TypeError:
                return False

        if operator == Operator.LTE:
            try:
                return field_value <= expected if field_value is not None else False
            except TypeError:
                return False

        if operator == Operator.CONTAINS:
            if field_value is None:
                return False
            # String containment or list membership
            try:
                return expected in field_value
            except TypeError:
                return False

        if operator == Operator.INTERSECTS:
            if field_value is None or expected is None:
                return False
            # Check if any elements are common between two lists
            try:
                return bool(set(field_value) & set(expected))
            except TypeError:
                return False

        # Should not reach here
        return False


@dataclass
class CompositeCondition:
    """
    Composite condition combining multiple conditions with logical operators.

    Supports AND (all must be true), OR (any must be true), and NOT (invert).
    Can be nested arbitrarily to create complex condition trees.

    Attributes:
        operator: Logical operator (AND, OR, NOT)
        conditions: List of conditions to combine
    """

    operator: Operator
    conditions: List[Union[Condition, "CompositeCondition"]]

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate this composite condition against the provided context.

        Args:
            context: Evaluation context containing request, query_features, etc.

        Returns:
            Boolean result of the composite evaluation
        """
        if self.operator == Operator.AND:
            return all(cond.evaluate(context) for cond in self.conditions)

        if self.operator == Operator.OR:
            return any(cond.evaluate(context) for cond in self.conditions)

        if self.operator == Operator.NOT:
            # NOT should have exactly one condition
            if len(self.conditions) != 1:
                raise ValueError("NOT operator requires exactly one condition")
            return not self.conditions[0].evaluate(context)

        raise ValueError(f"Invalid composite operator: {self.operator}")


class ConditionParser:
    """
    Parser for creating Condition/CompositeCondition from dict/YAML specs.

    Supports parsing both simple conditions and nested composite conditions
    from dictionary specifications.
    """

    @classmethod
    def parse(cls, spec: Dict[str, Any]) -> Union[Condition, CompositeCondition]:
        """
        Parse a condition specification into a Condition or CompositeCondition.

        Simple condition format:
            {"field": "mode", "operator": "EQ", "value": "resolve_one"}

        Composite condition format:
            {
                "operator": "AND",
                "conditions": [
                    {"field": "a", "operator": "EQ", "value": 1},
                    {"field": "b", "operator": "EQ", "value": 2}
                ]
            }

        Args:
            spec: Dictionary specification of the condition

        Returns:
            Parsed Condition or CompositeCondition instance
        """
        # Check if this is a composite condition (has "conditions" key)
        if "conditions" in spec:
            # Parse composite condition
            operator = Operator[spec["operator"]]
            conditions = [cls.parse(cond_spec) for cond_spec in spec["conditions"]]
            return CompositeCondition(operator=operator, conditions=conditions)
        else:
            # Parse simple condition
            field = spec["field"]
            operator = Operator[spec["operator"]]
            value = spec["value"]
            return Condition(field=field, operator=operator, value=value)


def build_eval_context(
    request: "IngestRequest",
    query_features: "QueryFeatures",
    execution_context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build the evaluation context for condition evaluation.

    This is the ONLY way to construct the evaluation context. It ensures
    consistent structure and includes all required fields for condition
    evaluation.

    The context includes:
    - request.*: All fields from IngestRequest
    - query_features.*: All fields from QueryFeatures
    - context.*: ExecutionContext fields (if provided)
    - Precomputed booleans: is_resolve_one, is_discover_many, has_geo_constraint

    Args:
        request: The ingestion request
        query_features: Extracted query features
        execution_context: Optional execution context dictionary

    Returns:
        Dictionary suitable for condition evaluation
    """
    from engine.orchestration.types import IngestionMode

    # Convert dataclasses to dicts for nested access
    request_dict = asdict(request)
    query_features_dict = asdict(query_features)

    # Build context with namespaced access
    context: Dict[str, Any] = {
        "request": request_dict,
        "query_features": query_features_dict,
    }

    # Add execution context if provided
    if execution_context is not None:
        context["context"] = execution_context

    # Add precomputed boolean shortcuts for convenience
    context["is_resolve_one"] = request.ingestion_mode == IngestionMode.RESOLVE_ONE
    context["is_discover_many"] = request.ingestion_mode == IngestionMode.DISCOVER_MANY
    # has_geo_constraint would require checking for bbox/geo_point in future
    context["has_geo_constraint"] = False  # Placeholder for future implementation

    return context
