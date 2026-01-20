"""
Base Extractor Interface

Defines the abstract BaseExtractor class that all extraction implementations
must follow to ensure consistent behavior across sources.
"""

import time
import re
from abc import ABC, abstractmethod
from typing import Dict, Tuple, List, Optional, Any

from engine.extraction.logging_config import (
    get_extraction_logger,
    log_extraction_start,
    log_extraction_success,
    log_extraction_failure,
)
from engine.extraction.entity_classifier import resolve_entity_class, get_engine_modules


class BaseExtractor(ABC):
    """
    Abstract base class for data extraction.

    Implementations are responsible for transforming raw ingestion payloads
    into structured listing fields, validating outputs, and separating
    schema-defined attributes from discovered attributes.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        Unique identifier for this extractor's data source.

        Returns:
            str: Source name (e.g., "google_places", "osm")
        """
        pass

    @abstractmethod
    def extract(self, raw_data: Dict) -> Dict:
        """
        Transform raw data into extracted listing fields.

        Args:
            raw_data: Raw ingestion payload for a single record

        Returns:
            Dict: Extracted fields mapped to schema names
        """
        pass

    @abstractmethod
    def validate(self, extracted: Dict) -> Dict:
        """
        Validate extracted fields against schema rules.

        Args:
            extracted: Extracted fields to validate

        Returns:
            Dict: Validated (and possibly normalized) fields
        """
        pass

    @abstractmethod
    def split_attributes(self, extracted: Dict) -> Tuple[Dict, Dict]:
        """
        Split extracted fields into schema-defined and discovered attributes.

        Args:
            extracted: Extracted fields to split

        Returns:
            Tuple[Dict, Dict]: (attributes, discovered_attributes)
        """
        pass

    def extract_rich_text(self, raw_data: Dict) -> List[str]:
        """
        Extract rich text descriptions from raw data for summary synthesis.

        This method extracts unstructured text content (reviews, descriptions,
        snippets, etc.) that can be used by the summary synthesizer to create
        high-quality summary fields.

        Default implementation returns an empty list. Extractors should override
        this method to return source-specific rich text.

        Args:
            raw_data: Raw ingestion payload for a single record

        Returns:
            List[str]: List of text descriptions/snippets from the raw data

        Examples:
            >>> extractor = GooglePlacesExtractor()
            >>> rich_text = extractor.extract_rich_text(raw_place_data)
            >>> # Returns: ["Editorial summary...", "Review 1 text...", "Review 2 text..."]
        """
        return []

    def extract_with_logging(
        self,
        raw_data: Dict,
        record_id: str,
        confidence_score: Optional[float] = None,
    ) -> Dict:
        """
        Wrapper method that executes extraction with structured logging.

        This method wraps the extract() call with start/success/failure logging,
        including timing and metadata capture.

        Args:
            raw_data: Raw ingestion payload for a single record
            record_id: RawIngestion record ID for tracking
            confidence_score: Optional confidence score for this extraction

        Returns:
            Dict: Extracted fields mapped to schema names

        Raises:
            Exception: Re-raises any exception from extract() after logging
        """
        logger = get_extraction_logger()
        extractor_name = self.__class__.__name__

        log_extraction_start(
            logger=logger,
            source=self.source_name,
            record_id=record_id,
            extractor=extractor_name,
        )

        start_time = time.time()

        try:
            extracted = self.extract(raw_data)
            duration = time.time() - start_time

            # Count non-null fields
            fields_extracted = sum(1 for v in extracted.values() if v is not None)

            log_extraction_success(
                logger=logger,
                source=self.source_name,
                record_id=record_id,
                extractor=extractor_name,
                duration_seconds=round(duration, 3),
                fields_extracted=fields_extracted,
                confidence_score=confidence_score,
            )

            return extracted

        except Exception as e:
            duration = time.time() - start_time

            log_extraction_failure(
                logger=logger,
                source=self.source_name,
                record_id=record_id,
                extractor=extractor_name,
                error=str(e),
                duration_seconds=round(duration, 3),
            )

            raise


def dedupe_preserve_order(values: List[str]) -> List[str]:
    """
    Deduplicate list while preserving insertion order.

    Used to avoid repeated module trigger evaluation and ensure
    deterministic output in the extraction pipeline.

    Args:
        values: List of strings (potentially with duplicates)

    Returns:
        List with duplicates removed, preserving first occurrence order

    Example:
        >>> dedupe_preserve_order(["padel", "tennis", "padel"])
        ["padel", "tennis"]
    """
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def extract_with_lens_contract(raw_data: Dict[str, Any], lens_contract: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract entity data using lens contract for mapping and dimension distribution.

    LensContract boundary: Engine receives lens_contract (plain dict), NEVER imports from lenses/
    Application bootstrap loads lens and injects LensContract into engine.

    This function implements the complete extraction pipeline:
    1. Extract raw categories from source
    2. Map to canonical values using LensContract mapping rules
    3. Dedupe canonical_values to avoid repeated trigger evaluation
    4. Distribute canonical values to dimensions by facet
    5. Resolve entity_class (deterministic, engine rules)
    6. Compute required modules (engine + lens triggers)
    7. Extract module attributes
    8. Build modules JSONB with namespacing
    9. Return structured entity with deduplicated text[] arrays

    Args:
        raw_data: Raw entity data from source (dict with categories, attributes, etc.)
        lens_contract: Plain dict (LensContract) containing:
            - facets: Dict mapping facet keys to {dimension_source, ...}
            - values: List of value dicts with {key, facet, display_name, ...}
            - mapping_rules: List of {pattern, canonical, confidence}
            - modules: Dict of module definitions
            - module_triggers: List of {when: {facet, value}, add_modules, conditions}

    Returns:
        Dict with extracted entity data:
            - entity_class: Single entity_class value
            - canonical_activities: List[str] (Postgres text[] array)
            - canonical_roles: List[str] (Postgres text[] array)
            - canonical_place_types: List[str] (Postgres text[] array)
            - canonical_access: List[str] (Postgres text[] array)
            - modules: Dict with namespaced JSONB structure {module_key: {fields}}

    Example:
        >>> lens_contract = {
        ...     "facets": {"activity": {"dimension_source": "canonical_activities"}},
        ...     "values": [{"key": "padel", "facet": "activity", "display_name": "Padel"}],
        ...     "mapping_rules": [{"pattern": r"(?i)\\bpadel\\b", "canonical": "padel", "confidence": 1.0}],
        ...     "modules": {},
        ...     "module_triggers": []
        ... }
        >>> extract_with_lens_contract({"categories": ["Padel Court"]}, lens_contract)
        {
            'entity_class': 'place',
            'canonical_activities': ['padel'],
            'canonical_roles': [],
            'canonical_place_types': ['sports_centre'],
            'canonical_access': [],
            'modules': {'core': {...}, 'location': {...}}
        }
    """
    # Step 1: Extract raw categories from source
    raw_categories = raw_data.get("categories", [])
    if not isinstance(raw_categories, list):
        raw_categories = [raw_categories] if raw_categories else []

    # Step 2: Map to canonical values using LensContract mapping rules
    # Access mapping_rules from lens_contract["mapping_rules"]
    mapping_rules = lens_contract.get("mapping_rules", [])
    confidence_threshold = lens_contract.get("confidence_threshold", 0.7)  # Configurable, defaults to 0.7
    canonical_values = []

    for raw_category in raw_categories:
        for rule in mapping_rules:
            pattern = rule.get("pattern")
            canonical = rule.get("canonical")
            confidence = rule.get("confidence", 1.0)

            if not pattern or not canonical:
                continue

            # Apply regex pattern
            if re.search(pattern, str(raw_category)):
                # Filter by confidence threshold
                if confidence >= confidence_threshold:
                    canonical_values.append(canonical)

    # Step 2a: Dedupe canonical_values to avoid repeated trigger evaluation
    canonical_values = dedupe_preserve_order(canonical_values)

    # Step 3: Distribute canonical values to dimensions by facet
    # Initialize dimensions dict with actual DB column names
    dimensions = {
        "canonical_activities": [],
        "canonical_roles": [],
        "canonical_place_types": [],
        "canonical_access": []
    }

    # Build facet_to_dimension lookup from lens_contract["facets"]
    # Maps facet key to dimension_source (actual DB column name)
    facets_config = lens_contract.get("facets", {})
    facet_to_dimension = {}
    for facet_key, facet_data in facets_config.items():
        dimension_source = facet_data.get("dimension_source")
        if dimension_source:
            facet_to_dimension[facet_key] = dimension_source

    # Build values_by_key index from lens_contract["values"] list for efficient lookups
    values_list = lens_contract.get("values", [])
    values_by_key = {value["key"]: value for value in values_list if "key" in value}

    # Initialize canonical_values_by_facet with EMPTY LISTS for all facets from lens_contract["facets"]
    canonical_values_by_facet = {facet_key: [] for facet_key in facets_config.keys()}

    # Iterate through canonical_values and distribute to dimensions
    for value_key in canonical_values:
        # Find value in values_by_key index (built from lens_contract["values"])
        value_obj = values_by_key.get(value_key)
        if not value_obj:
            continue

        # Get facet from value["facet"]
        facet_key = value_obj.get("facet")
        if not facet_key:
            continue

        # Get dimension column name from facet_to_dimension lookup
        dimension_col = facet_to_dimension.get(facet_key)
        if not dimension_col:
            continue

        # Append value key to dimension array
        if dimension_col in dimensions:
            dimensions[dimension_col].append(value_key)

        # Track by facet key in canonical_values_by_facet dict
        if facet_key in canonical_values_by_facet:
            canonical_values_by_facet[facet_key].append(value_key)

    # Deduplicate dimension arrays before persistence
    for dim_key in dimensions:
        dimensions[dim_key] = dedupe_preserve_order(dimensions[dim_key])

    # Deduplicate canonical_values_by_facet dict
    for facet_key in canonical_values_by_facet:
        canonical_values_by_facet[facet_key] = dedupe_preserve_order(canonical_values_by_facet[facet_key])

    # Step 4: Resolve entity_class (deterministic, engine rules - no lens dependency)
    classification_result = resolve_entity_class(raw_data)
    entity_class = classification_result["entity_class"]

    # Merge classification results into dimensions
    # The classifier returns canonical_roles, canonical_activities, canonical_place_types
    # We need to merge these with what we extracted from lens mapping
    for dim_name in ["canonical_activities", "canonical_roles", "canonical_place_types"]:
        classifier_values = classification_result.get(dim_name, [])
        if classifier_values:
            # Merge and dedupe
            combined = dimensions[dim_name] + classifier_values
            dimensions[dim_name] = dedupe_preserve_order(combined)

            # Also update canonical_values_by_facet for trigger matching
            # Need to map dimension name back to facet key
            for facet_key, dim_source in facet_to_dimension.items():
                if dim_source == dim_name:
                    combined_facet = canonical_values_by_facet.get(facet_key, []) + classifier_values
                    canonical_values_by_facet[facet_key] = dedupe_preserve_order(combined_facet)

    # Step 5: Compute required modules
    # Get engine modules (entity_class-based, from engine config)
    engine_modules = get_engine_modules(entity_class)
    required_modules = set(engine_modules)

    # Get lens modules from lens_contract["module_triggers"]
    module_triggers = lens_contract.get("module_triggers", [])
    for trigger in module_triggers:
        # Check if trigger matches using canonical_values_by_facet
        when_clause = trigger.get("when", {})
        facet = when_clause.get("facet")
        value = when_clause.get("value")

        if not facet or not value:
            continue

        # Check if entity has this value in the specified facet
        facet_values = canonical_values_by_facet.get(facet, [])
        if value not in facet_values:
            continue

        # Check entity_class conditions
        conditions = trigger.get("conditions", [])
        conditions_met = True
        for condition in conditions:
            if "entity_class" in condition:
                if condition["entity_class"] != entity_class:
                    conditions_met = False
                    break

        if not conditions_met:
            continue

        # Add triggered modules to required_modules
        add_modules = trigger.get("add_modules", [])
        required_modules.update(add_modules)

    # Step 6: Extract module attributes (using lens_contract["modules"] definitions)
    # Step 7: Build modules JSONB with namespacing
    modules_data = {}
    modules_config = lens_contract.get("modules", {})

    for module_name in required_modules:
        # For now, create empty module structure
        # In a real implementation, this would extract fields from raw_data
        # based on module_def field definitions
        module_def = modules_config.get(module_name, {})

        # Initialize module with empty fields structure
        # Real implementation would populate from raw_data based on module_def["fields"]
        modules_data[module_name] = {}

    # Step 8: Return structured entity with deduplicated text[] arrays for dimensions
    return {
        "entity_class": entity_class,
        "canonical_activities": dimensions["canonical_activities"],
        "canonical_roles": dimensions["canonical_roles"],
        "canonical_place_types": dimensions["canonical_place_types"],
        "canonical_access": dimensions["canonical_access"],
        "modules": modules_data
    }

