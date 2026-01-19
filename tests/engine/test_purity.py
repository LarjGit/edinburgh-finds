"""
Engine Purity Tests

Tests to ensure engine layer maintains architectural purity:
- No imports from lenses/ directory (LensContract boundary violation)
- No literal string comparisons against dimension values (structural purity violation)

These tests enforce the engine-lens separation by preventing:
1. Direct coupling between engine and lens code
2. Value-based branching in engine (engine should only branch on entity_class)
"""

import glob
import re
from pathlib import Path


def test_engine_does_not_import_lenses():
    """Engine layer must never import from lenses/ directory.

    This test prevents LensContract boundary violations. The engine must remain
    completely decoupled from lens implementations to maintain the architecture.
    """
    engine_dir = Path(__file__).parent.parent.parent / "engine"
    engine_files = list(engine_dir.glob("**/*.py"))

    # Pattern to match actual import statements (not comments or strings)
    # Matches: from lenses... or import lenses...
    # At the start of a line (after optional whitespace)
    import_pattern = r'^\s*(from\s+lenses|import\s+lenses)'

    violations = []
    for file_path in engine_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

            for line_no, line in enumerate(lines, 1):
                # Skip comment-only lines
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue

                # Check for actual import statements
                if re.match(import_pattern, line):
                    violations.append(f"{file_path.relative_to(engine_dir.parent)}:{line_no} - {line.strip()}")

    assert not violations, (
        f"Engine imports from lenses/ (LensContract boundary violation):\n" +
        "\n".join(violations)
    )


def test_engine_no_literal_string_comparisons_on_dimensions():
    """Engine must not compare dimension values against literal strings.

    Structural purity rules:
    Engine may only:
    - Branch on entity_class (e.g., if entity_class == "place")
    - Perform set operations on opaque strings (union, intersection, membership)
    - Check emptiness/existence (e.g., if canonical_activities)
    - Pass opaque strings through unchanged

    FORBIDDEN: Literal comparisons like:
    - if "padel" in canonical_activities
    - if canonical_roles[0] == "coach"
    - elif "winery" in canonical_place_types

    This ensures engine remains vertical-agnostic.
    """
    engine_dir = Path(__file__).parent.parent.parent / "engine"
    engine_files = list(engine_dir.glob("**/*.py"))

    # Pattern: Detect literal string comparisons against dimension array values
    # This catches patterns like: if "value" in canonical_*, if canonical_*[0] == "value"
    # We need to match both single and double quotes
    forbidden_pattern = r'(if|elif)\s+.*(?:canonical_activities|canonical_roles|canonical_place_types|canonical_access).*(?:==|in)\s*["\']'

    violations = []
    for file_path in engine_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

            for line_no, line in enumerate(lines, 1):
                matches = re.search(forbidden_pattern, line)
                if matches:
                    violations.append(f"{file_path.relative_to(engine_dir.parent)}:{line_no} - {line.strip()}")

    assert not violations, (
        f"Engine has literal string comparisons against dimension values (structural purity violation):\n" +
        "\n".join(violations) +
        "\n\nEngine may only: branch on entity_class, perform set operations, check emptiness, pass through unchanged"
    )
