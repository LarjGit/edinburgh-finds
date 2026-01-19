"""
Module composition validator.

Enforces architectural contracts for module composition:
- CONTRACT 1: modules JSONB must be namespaced by module key (not flattened)
- CONTRACT 2: No duplicate module keys in YAML configuration

All validation is fail-fast: errors raise ModuleValidationError immediately.
"""

import yaml
from pathlib import Path
from typing import Any, Dict


class ModuleValidationError(Exception):
    """Raised when module composition violates architectural contracts."""
    pass


def validate_modules_namespacing(modules_data: Dict[str, Any]) -> None:
    """
    Validate that modules JSONB is properly namespaced, not flattened.

    CONTRACT 1: modules JSONB MUST be namespaced by module key.

    Correct structure:
        {
            "location": {"latitude": 55.95, "longitude": -3.18},
            "contact": {"phone": "+44 131 555 0100"},
            "sports_facility": {"inventory": {...}}
        }

    Wrong structure (flattened):
        {"latitude": 55.95, "longitude": -3.18, "phone": "+44 131 555 0100"}

    Args:
        modules_data: Modules dict to validate

    Raises:
        ModuleValidationError: If modules are flattened instead of namespaced

    Note:
        Duplicate field names across DIFFERENT modules are ALLOWED due to
        namespacing (e.g., sports_facility.name and wine_production.name).
    """
    if not modules_data:
        # Empty dict is valid
        return

    # Heuristic to detect flattened structure:
    # If all values are primitives or lists (not dicts), it's likely flattened.
    # Properly namespaced modules have dict values representing module data.

    # Check if this looks like a flattened structure
    # Flattened: all top-level keys are field names (values are primitives/lists)
    # Namespaced: all top-level keys are module names (values are dicts)

    non_dict_values = []
    for key, value in modules_data.items():
        if not isinstance(value, dict):
            non_dict_values.append(key)

    # If we have non-dict values at the top level, this is likely flattened
    if non_dict_values:
        raise ModuleValidationError(
            f"modules JSONB must be namespaced by module key, not flattened. "
            f"Found non-dict values for keys: {', '.join(non_dict_values)}. "
            f"Expected structure: {{'module_name': {{'field': value}}}}"
        )


class DuplicateKeyError(yaml.YAMLError):
    """Raised when duplicate keys are found in YAML."""
    pass


class StrictYAMLLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate keys."""

    def construct_mapping(self, node, deep=False):
        """Override to detect duplicate keys."""
        if not isinstance(node, yaml.MappingNode):
            raise yaml.constructor.ConstructorError(
                None, None,
                f"expected a mapping node, but found {node.id}",
                node.start_mark
            )

        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)

            # Check for duplicate keys
            if key in mapping:
                raise DuplicateKeyError(
                    f"Duplicate key found: '{key}' at line {key_node.start_mark.line + 1}. "
                    f"Each key must be unique within its scope."
                )

            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value

        return mapping


def load_yaml_strict(yaml_path: Path) -> Dict[str, Any]:
    """
    Load YAML file with strict duplicate key checking.

    Args:
        yaml_path: Path to YAML file

    Returns:
        Parsed YAML as dict

    Raises:
        DuplicateKeyError: If duplicate keys found at any level
        yaml.YAMLError: If YAML is malformed
        FileNotFoundError: If file doesn't exist

    Example:
        >>> data = load_yaml_strict(Path("config.yaml"))
    """
    yaml_path = Path(yaml_path)

    with open(yaml_path, 'r', encoding='utf-8') as f:
        try:
            data = yaml.load(f, Loader=StrictYAMLLoader)
        except DuplicateKeyError as e:
            # Re-raise with context
            raise ModuleValidationError(
                f"Duplicate keys detected in {yaml_path}: {e}"
            ) from e
        except yaml.YAMLError as e:
            # Re-raise YAML errors as-is
            raise

    if not isinstance(data, dict):
        raise ModuleValidationError(
            f"Invalid YAML in {yaml_path}: Expected dict, got {type(data).__name__}"
        )

    return data
