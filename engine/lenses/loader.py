"""
Lens configuration loader.

Loads and validates lens.yaml configuration files, enforcing all architectural
contracts via fail-fast validation at load time.
"""

import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.lenses.validator import validate_lens_config, ValidationError
from engine.modules.validator import load_yaml_strict, validate_modules_namespacing, ModuleValidationError


class LensConfigError(Exception):
    """Raised when lens configuration file cannot be loaded or is invalid."""
    pass


def dedupe_preserve_order(values: List[str]) -> List[str]:
    """
    Deduplicate list while preserving insertion order.

    Args:
        values: List of strings (potentially with duplicates)

    Returns:
        List with duplicates removed, preserving first occurrence order

    Example:
        >>> dedupe_preserve_order(["a", "b", "c", "b", "a"])
        ["a", "b", "c"]
    """
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


class FacetDefinition:
    """
    Represents a facet configuration.

    A facet defines how a dimension (canonical_activities, canonical_roles, etc.)
    is displayed and interpreted in the lens.
    """

    def __init__(self, key: str, data: Dict[str, Any]):
        """
        Initialize facet definition.

        Args:
            key: Facet key (e.g., "activity", "role", "place_type")
            data: Facet configuration from lens.yaml
        """
        self.key = key
        self.dimension_source = data.get("dimension_source")
        self.ui_label = data.get("ui_label")
        self.display_mode = data.get("display_mode")
        self.order = data.get("order", 999)
        self.show_in_filters = data.get("show_in_filters", False)
        self.show_in_navigation = data.get("show_in_navigation", False)
        self.icon = data.get("icon")


class CanonicalValue:
    """
    Represents a canonical value with all interpretation metadata.

    Canonical values are the lens-level interpretation of dimension values,
    including display names, descriptions, SEO data, icons, colors, etc.
    """

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize canonical value.

        Args:
            data: Value configuration from lens.yaml
        """
        self.key = data.get("key")
        self.facet = data.get("facet")
        self.display_name = data.get("display_name")
        self.description = data.get("description")
        self.seo_slug = data.get("seo_slug")
        self.search_keywords = data.get("search_keywords", [])
        self.icon_url = data.get("icon_url")
        self.color = data.get("color")


class DerivedGrouping:
    """
    Represents a derived grouping configuration.

    Derived groupings are computed at query time based on entity attributes.
    They are NOT stored in the database (DERIVED/VIEW-ONLY).

    Matching logic:
    - AND-within-rule: All conditions in a rule must match
    - OR-across-rules: Any rule can match
    """

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize derived grouping.

        Args:
            data: Grouping configuration from lens.yaml

        Note:
            Grouping is DERIVED/VIEW-ONLY, not stored in database.
        """
        self.id = data.get("id")
        self.label = data.get("label")
        self.description = data.get("description")
        self.rules = data.get("rules", [])

    def matches(self, entity: Dict[str, Any]) -> bool:
        """
        Check if entity matches this grouping.

        Logic:
        - AND-within-rule: All conditions in a rule must match
        - OR-across-rules: Any rule can match

        Args:
            entity: Entity dict with entity_class and canonical_roles

        Returns:
            True if entity matches any rule, False otherwise
        """
        # OR-across-rules: Any rule can match
        for rule in self.rules:
            if self._matches_rule(entity, rule):
                return True
        return False

    def _matches_rule(self, entity: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """
        Check if entity matches a single rule.

        All conditions within a rule must match (AND logic).

        Args:
            entity: Entity dict with entity_class and canonical_roles
            rule: Rule configuration

        Returns:
            True if entity matches all conditions in rule
        """
        # Check entity_class condition
        if "entity_class" in rule:
            if entity.get("entity_class") != rule["entity_class"]:
                return False

        # Check roles condition (entity must have at least one of required roles)
        if "roles" in rule:
            required_roles = rule["roles"]
            entity_roles = entity.get("canonical_roles", [])

            # Entity must have at least one of the required roles
            if not any(role in entity_roles for role in required_roles):
                return False

        # All conditions matched
        return True


class ModuleTrigger:
    """
    Represents a module trigger configuration.

    Module triggers define when to apply domain modules based on facet values.

    NOTE: facet refers to the canonical value's facet key as defined by the lens
    (i.e., lens.facets keys), e.g. activity, role, wine_type, venue_type,
    NOT the DB column name (canonical_activities, canonical_roles, etc.).

    Example:
        {
            "when": {"facet": "activity", "value": "padel"},
            "add_modules": ["sports_facility"],
            "conditions": [{"entity_class": "place"}]
        }
    """

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize module trigger.

        Args:
            data: Trigger configuration from lens.yaml with explicit list format
        """
        when = data.get("when", {})
        self.facet = when.get("facet")
        self.value = when.get("value")
        self.add_modules = data.get("add_modules", [])
        self.conditions = data.get("conditions", [])

    def matches(self, entity_class: str, canonical_values_by_facet: Dict[str, List[str]]) -> bool:
        """
        Check if trigger should fire for this entity.

        Args:
            entity_class: Entity class (place, person, organization, event, thing)
            canonical_values_by_facet: Dict mapping facet keys (as defined by the lens)
                                      to lists of canonical values.
                                      Example: {
                                          "activity": ["padel", "tennis"],
                                          "role": ["provides_facility"],
                                          "place_type": ["sports_centre"]
                                      }

        Returns:
            True if trigger should fire, False otherwise
        """
        # Check if entity has the required value in the specified facet
        facet_values = canonical_values_by_facet.get(self.facet, [])
        if self.value not in facet_values:
            return False

        # Check additional conditions (all must match - AND logic)
        for condition in self.conditions:
            if "entity_class" in condition:
                if entity_class != condition["entity_class"]:
                    return False

        return True


class ModuleDefinition:
    """
    Represents a domain module definition.

    Domain modules are vertical-specific data structures (e.g., sports_facility,
    wine_production) defined in the lens layer.
    """

    def __init__(self, name: str, data: Dict[str, Any]):
        """
        Initialize module definition.

        Args:
            name: Module name (e.g., "sports_facility")
            data: Module configuration from lens.yaml
        """
        self.name = name
        self.description = data.get("description")
        self.fields = data.get("fields", {})


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

        # Parse configuration into structured objects
        self._facets = self._parse_facets()
        self._values = self._parse_values()
        self._values_by_facet = self._build_values_by_facet()
        self._groupings = self._parse_derived_groupings()
        self._modules = self._parse_modules()
        self._triggers = self._parse_module_triggers()
        self._confidence_threshold = self.config.get("confidence_threshold", 0.7)  # Configurable, defaults to 0.7

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Load YAML configuration file with strict duplicate key checking.

        Args:
            config_path: Path to lens.yaml file

        Returns:
            Parsed configuration dictionary

        Raises:
            LensConfigError: If file cannot be read, parsed, or has duplicate keys
        """
        try:
            # Use strict YAML loader that rejects duplicate keys
            config = load_yaml_strict(config_path)

            # Validate module namespacing if modules section exists
            if "modules" in config:
                try:
                    validate_modules_namespacing(config["modules"])
                except ModuleValidationError as e:
                    raise LensConfigError(
                        f"Invalid module structure in {config_path}: {e}"
                    ) from e

            return config

        except FileNotFoundError as e:
            raise LensConfigError(
                f"Lens config file not found: {config_path}"
            ) from e

        except ModuleValidationError as e:
            # Duplicate key errors come through as ModuleValidationError
            raise LensConfigError(
                f"Invalid lens config in {config_path}: {e}"
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
        return self.config.get("modules", {})

    @property
    def module_triggers(self) -> list:
        """Get module triggers configuration."""
        return self.config.get("module_triggers", [])

    @property
    def confidence_threshold(self) -> float:
        """Get confidence threshold for mapping rules. Defaults to 0.7."""
        return self._confidence_threshold

    def _parse_facets(self) -> Dict[str, FacetDefinition]:
        """Parse facets configuration into FacetDefinition objects."""
        facets_config = self.config.get("facets", {})
        return {
            key: FacetDefinition(key, data)
            for key, data in facets_config.items()
        }

    def _parse_values(self) -> Dict[str, CanonicalValue]:
        """Parse values configuration into CanonicalValue objects."""
        values_config = self.config.get("values", [])
        return {
            value_data["key"]: CanonicalValue(value_data)
            for value_data in values_config
            if "key" in value_data
        }

    def _build_values_by_facet(self) -> Dict[str, List[CanonicalValue]]:
        """Build index of values grouped by facet."""
        values_by_facet: Dict[str, List[CanonicalValue]] = {}
        for value in self._values.values():
            if value.facet not in values_by_facet:
                values_by_facet[value.facet] = []
            values_by_facet[value.facet].append(value)
        return values_by_facet

    def _parse_derived_groupings(self) -> List[DerivedGrouping]:
        """Parse derived groupings configuration into DerivedGrouping objects."""
        groupings_config = self.config.get("derived_groupings", [])
        return [DerivedGrouping(data) for data in groupings_config]

    def _parse_modules(self) -> Dict[str, ModuleDefinition]:
        """Parse modules configuration into ModuleDefinition objects."""
        modules_config = self.config.get("modules", {})
        return {
            name: ModuleDefinition(name, data)
            for name, data in modules_config.items()
        }

    def _parse_module_triggers(self) -> List[ModuleTrigger]:
        """Parse module triggers configuration into ModuleTrigger objects."""
        triggers_config = self.config.get("module_triggers", [])
        return [ModuleTrigger(data) for data in triggers_config]

    def map_raw_category(self, raw_category: str) -> List[str]:
        """
        Apply mapping rules to raw category string.

        Args:
            raw_category: Raw category string from data source

        Returns:
            List of canonical value keys (filtered by configured confidence threshold)
        """
        matching_values = []
        confidence_threshold = self._confidence_threshold

        for rule in self.mapping_rules:
            pattern = rule.get("pattern")
            canonical = rule.get("canonical")
            confidence = rule.get("confidence", 1.0)

            if not pattern or not canonical:
                continue

            # Apply regex pattern
            if re.search(pattern, raw_category):
                # Filter by confidence threshold
                if confidence >= confidence_threshold:
                    matching_values.append(canonical)

        return matching_values

    def get_values_by_facet(self, facet_key: str) -> List[CanonicalValue]:
        """
        Get all values for a specific facet.

        Args:
            facet_key: Facet key (e.g., "activity", "role")

        Returns:
            List of CanonicalValue objects for this facet
        """
        return self._values_by_facet.get(facet_key, [])

    def get_facets_sorted(self) -> List[FacetDefinition]:
        """
        Get all facets sorted by order field.

        Returns:
            List of FacetDefinition objects sorted by order
        """
        return sorted(self._facets.values(), key=lambda f: f.order)

    def compute_grouping(self, entity: Dict[str, Any]) -> Optional[str]:
        """
        Compute derived grouping for entity.

        Grouping is computed at query time, not stored in database.

        Args:
            entity: Entity dict with entity_class and canonical_roles

        Returns:
            First matching grouping id, or None if no match
        """
        for grouping in self._groupings:
            if grouping.matches(entity):
                return grouping.id
        return None

    def get_required_modules(self, entity_class: str, canonical_values_by_facet: Dict[str, List[str]]) -> List[str]:
        """
        Get required modules for entity based on module triggers.

        Args:
            entity_class: Entity class (place, person, organization, event, thing)
            canonical_values_by_facet: Dict mapping facet keys to lists of canonical values

        Returns:
            List of module names that should be applied
        """
        required_modules = []

        for trigger in self._triggers:
            if trigger.matches(entity_class, canonical_values_by_facet):
                required_modules.extend(trigger.add_modules)

        # Deduplicate while preserving order
        return dedupe_preserve_order(required_modules)


class LensRegistry:
    """
    Registry for managing lens instances.

    Provides global access to loaded lenses by lens_id.
    """

    _lenses: Dict[str, VerticalLens] = {}

    @classmethod
    def register(cls, lens_id: str, config_path: Path) -> None:
        """
        Register a lens by loading its configuration.

        Args:
            lens_id: Unique identifier for the lens
            config_path: Path to lens.yaml file
        """
        lens = VerticalLens(config_path)
        cls._lenses[lens_id] = lens

    @classmethod
    def get_lens(cls, lens_id: str) -> VerticalLens:
        """
        Get a registered lens by ID.

        Args:
            lens_id: Lens identifier

        Returns:
            VerticalLens instance

        Raises:
            KeyError: If lens_id not found
        """
        if lens_id not in cls._lenses:
            raise KeyError(f"Lens '{lens_id}' not found in registry")
        return cls._lenses[lens_id]

    @classmethod
    def load_all(cls, lenses_dir: Path) -> None:
        """
        Load all lenses from a directory.

        Expects directory structure:
            lenses_dir/
                lens1/lens.yaml
                lens2/lens.yaml
                ...

        Args:
            lenses_dir: Directory containing lens folders
        """
        lenses_dir = Path(lenses_dir)

        for lens_folder in lenses_dir.iterdir():
            if lens_folder.is_dir():
                config_path = lens_folder / "lens.yaml"
                if config_path.exists():
                    lens_id = lens_folder.name
                    cls.register(lens_id, config_path)
