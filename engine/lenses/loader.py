"""
Lens configuration loader.

Loads and validates lens.yaml configuration files, enforcing all architectural
contracts via fail-fast validation at load time.
"""

import yaml
from pathlib import Path
from typing import Any, Dict

from engine.lenses.validator import validate_lens_config, ValidationError


class LensConfigError(Exception):
    """Raised when lens configuration file cannot be loaded or is invalid."""
    pass


class VerticalLens:
    """
    Represents a vertical-specific lens configuration.

    A lens defines how the universal engine should interpret and display
    entities for a specific vertical (e.g., sports, wine, restaurants).

    The lens owns all vertical-specific knowledge:
    - Facets (how dimensions are displayed and interpreted)
    - Values (canonical value definitions with display metadata)
    - Mapping rules (how raw data maps to canonical values)
    - Derived groupings (how entities are grouped for navigation)
    - Domain modules (vertical-specific data structures)
    - Module triggers (when to apply domain modules)

    Validation is fail-fast: configuration errors raise LensConfigError
    immediately at initialization time (not at runtime).
    """

    def __init__(self, config_path: Path):
        """
        Load and validate lens configuration from YAML file.

        Args:
            config_path: Path to lens.yaml file

        Raises:
            LensConfigError: If config file cannot be loaded or validation fails
        """
        self.config_path = config_path
        self.config = self._load_config(config_path)

        # FAIL-FAST: Validate configuration against all architectural contracts
        try:
            validate_lens_config(self.config)
        except ValidationError as e:
            raise LensConfigError(
                f"Invalid lens config in {config_path}: {e}"
            ) from e

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Load YAML configuration file.

        Args:
            config_path: Path to lens.yaml file

        Returns:
            Parsed configuration dictionary

        Raises:
            LensConfigError: If file cannot be read or parsed
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                raise LensConfigError(
                    f"Invalid lens config in {config_path}: "
                    f"Expected dict, got {type(config).__name__}"
                )

            return config

        except FileNotFoundError as e:
            raise LensConfigError(
                f"Lens config file not found: {config_path}"
            ) from e

        except yaml.YAMLError as e:
            raise LensConfigError(
                f"Failed to parse YAML in {config_path}: {e}"
            ) from e

        except Exception as e:
            raise LensConfigError(
                f"Failed to load lens config from {config_path}: {e}"
            ) from e

    @property
    def facets(self) -> Dict[str, Any]:
        """Get facets configuration."""
        return self.config.get("facets", {})

    @property
    def values(self) -> list:
        """Get values configuration."""
        return self.config.get("values", [])

    @property
    def mapping_rules(self) -> list:
        """Get mapping rules configuration."""
        return self.config.get("mapping_rules", [])

    @property
    def derived_groupings(self) -> list:
        """Get derived groupings configuration."""
        return self.config.get("derived_groupings", [])

    @property
    def domain_modules(self) -> Dict[str, Any]:
        """Get domain modules configuration."""
        return self.config.get("domain_modules", {})

    @property
    def module_triggers(self) -> list:
        """Get module triggers configuration."""
        return self.config.get("module_triggers", [])
