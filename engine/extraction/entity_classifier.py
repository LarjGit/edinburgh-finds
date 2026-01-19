"""
Entity classification logic for Edinburgh Finds engine.

This module implements the deterministic algorithm for classifying entities
according to the single entity_class + multi roles pattern.

See engine/docs/classification_rules.md for complete specification.
"""

from typing import Dict, List, Any, Optional


# Valid entity_class values (see classification_rules.md)
VALID_ENTITY_CLASSES = {"place", "person", "organization", "event", "thing"}


def validate_entity_class(entity_class: str) -> None:
    """
    Validate that entity_class is one of the allowed values.

    Args:
        entity_class: The entity_class value to validate

    Raises:
        AssertionError: If entity_class is not one of: place, person, organization, event, thing

    See: engine/docs/classification_rules.md for valid values
    """
    assert entity_class in VALID_ENTITY_CLASSES, \
        f"entity_class must be one of: {', '.join(sorted(VALID_ENTITY_CLASSES))}. Got: {entity_class}"


def has_time_bounds(raw_data: Dict[str, Any]) -> bool:
    """
    Check if entity has time bounds (start/end times).

    Args:
        raw_data: Raw entity data dictionary

    Returns:
        True if entity has start_datetime or end_datetime, False otherwise

    Priority: Highest (1) - see classification_rules.md
    """
    return bool(
        raw_data.get("start_datetime") or
        raw_data.get("end_datetime") or
        raw_data.get("start_date") or
        raw_data.get("end_date")
    )


def has_location(raw_data: Dict[str, Any]) -> bool:
    """
    Check if entity has physical location (coordinates or street address).

    Args:
        raw_data: Raw entity data dictionary

    Returns:
        True if entity has latitude/longitude or street address, False otherwise

    Priority: 2 - see classification_rules.md
    """
    has_coordinates = bool(
        raw_data.get("latitude") and raw_data.get("longitude")
    )
    has_address = bool(
        raw_data.get("address") or
        raw_data.get("street_address")
    )
    return has_coordinates or has_address


def is_individual(raw_data: Dict[str, Any]) -> bool:
    """
    Check if entity represents a named individual.

    Args:
        raw_data: Raw entity data dictionary

    Returns:
        True if entity represents an individual person, False otherwise

    Priority: 3 - see classification_rules.md
    """
    # Check type hints
    entity_type = raw_data.get("type", "").lower()
    if entity_type in {"coach", "instructor", "teacher", "trainer", "person"}:
        return True

    # Check categories
    categories = raw_data.get("categories", [])
    if isinstance(categories, list):
        category_str = " ".join(categories).lower()
        if any(term in category_str for term in ["coach", "instructor", "trainer"]):
            # Could be individual or organization - need more context
            # If no address/location, likely individual
            if not has_location(raw_data):
                return True

    return False


def is_organization_like(raw_data: Dict[str, Any]) -> bool:
    """
    Check if entity represents an organization/group/business.

    Args:
        raw_data: Raw entity data dictionary

    Returns:
        True if entity is organization-like, False otherwise

    Priority: 4 - see classification_rules.md
    """
    entity_type = raw_data.get("type", "").lower()
    org_types = {"retailer", "shop", "business", "organization", "league", "club", "association"}

    if entity_type in org_types:
        return True

    categories = raw_data.get("categories", [])
    if isinstance(categories, list):
        category_str = " ".join(categories).lower()
        if any(term in category_str for term in ["retail", "shop", "business", "league", "chain"]):
            return True

    return False


def extract_roles(raw_data: Dict[str, Any]) -> List[str]:
    """
    Extract roles (canonical_roles) from raw entity data.

    Args:
        raw_data: Raw entity data dictionary

    Returns:
        List of role strings (e.g., ["provides_facility", "membership_org"])

    See: engine/docs/classification_rules.md for role definitions
    """
    roles = []

    # Check for facility provision
    if raw_data.get("has_courts") or raw_data.get("has_pitches"):
        roles.append("provides_facility")

    # Check for membership organization
    if raw_data.get("membership_required"):
        roles.append("membership_org")

    # Check for instruction provision
    entity_type = raw_data.get("type", "").lower()
    categories = raw_data.get("categories", [])
    category_str = " ".join(categories).lower() if isinstance(categories, list) else ""

    if entity_type in {"coach", "instructor", "trainer"} or \
       any(term in category_str for term in ["coach", "instructor", "trainer"]) or \
       raw_data.get("provides_coaching"):
        roles.append("provides_instruction")

    # Check for retail/goods sales
    if entity_type in {"retailer", "shop"} or \
       any(term in category_str for term in ["retail", "shop"]):
        roles.append("sells_goods")

    # Deduplicate
    return list(set(roles))


def extract_activities(raw_data: Dict[str, Any]) -> List[str]:
    """
    Extract activities (canonical_activities) from raw entity data.

    Args:
        raw_data: Raw entity data dictionary

    Returns:
        List of activity strings (e.g., ["tennis", "padel"])
    """
    activities = raw_data.get("activities", [])
    if not isinstance(activities, list):
        return []

    # Normalize to lowercase and deduplicate
    return list(set(activity.lower() for activity in activities))


def extract_place_types(raw_data: Dict[str, Any]) -> List[str]:
    """
    Extract place types (canonical_place_types) from raw entity data.

    Args:
        raw_data: Raw entity data dictionary

    Returns:
        List of place_type strings (e.g., ["sports_centre"])

    Note: Only applicable to entities with entity_class='place'
    """
    place_types = []

    # Check categories for place type hints
    categories = raw_data.get("categories", [])
    if isinstance(categories, list):
        category_str = " ".join(categories).lower()

        if any(term in category_str for term in ["sports centre", "sports center", "sports facility"]):
            place_types.append("sports_centre")
        elif any(term in category_str for term in ["outdoor", "field", "pitch"]):
            place_types.append("outdoor_facility")

    return place_types if place_types else ["sports_centre"]  # Default for sports entities


def resolve_entity_class(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve entity_class and roles using deterministic priority algorithm.

    This is the main entry point for entity classification. It implements
    the priority-based algorithm defined in classification_rules.md:

    Priority (highest first):
    1. Time-bounded → event
    2. Physical location → place
    3. Membership/group → organization
    4. Named individual → person
    5. Fallback → thing

    Args:
        raw_data: Raw entity data dictionary with fields like:
            - name: Entity name
            - type: Entity type hint
            - categories: List of category strings
            - start_datetime, end_datetime: Time bounds
            - latitude, longitude: Coordinates
            - address: Street address
            - has_courts, has_pitches: Facility indicators
            - membership_required: Membership indicator
            - activities: List of activity strings

    Returns:
        Dictionary with classified entity data:
            - entity_class: Single entity_class value (place, person, organization, event, thing)
            - canonical_roles: List of role strings (may be empty)
            - canonical_activities: List of activity strings
            - canonical_place_types: List of place_type strings (only if entity_class='place')

    Raises:
        AssertionError: If resolved entity_class is not one of the 5 valid values

    See: engine/docs/classification_rules.md for complete specification

    Examples:
        >>> # Club with courts → place + roles
        >>> resolve_entity_class({
        ...     "name": "Tennis Club",
        ...     "address": "123 Court St",
        ...     "has_courts": True,
        ...     "membership_required": True,
        ...     "activities": ["tennis"]
        ... })
        {
            'entity_class': 'place',
            'canonical_roles': ['provides_facility', 'membership_org'],
            'canonical_activities': ['tennis'],
            'canonical_place_types': ['sports_centre']
        }

        >>> # Freelance coach → person + role
        >>> resolve_entity_class({
        ...     "name": "Sarah Wilson",
        ...     "type": "coach",
        ...     "activities": ["tennis"]
        ... })
        {
            'entity_class': 'person',
            'canonical_roles': ['provides_instruction'],
            'canonical_activities': ['tennis'],
            'canonical_place_types': []
        }

        >>> # Tournament → event + no roles
        >>> resolve_entity_class({
        ...     "name": "Padel Open",
        ...     "start_datetime": "2024-05-15T09:00:00Z",
        ...     "activities": ["padel"]
        ... })
        {
            'entity_class': 'event',
            'canonical_roles': [],
            'canonical_activities': ['padel'],
            'canonical_place_types': []
        }
    """
    # Priority 1: Time-bounded → event (HIGHEST PRIORITY)
    # See: classification_rules.md - Priority Order
    if has_time_bounds(raw_data):
        entity_class = "event"

    # Priority 2: Physical location → place
    elif has_location(raw_data):
        entity_class = "place"

    # Priority 3: Named individual → person
    elif is_individual(raw_data):
        entity_class = "person"

    # Priority 4: Organization/group/business → organization
    elif is_organization_like(raw_data):
        entity_class = "organization"

    # Priority 5: Fallback → thing
    else:
        entity_class = "thing"

    # Validate entity_class (see classification_rules.md - Validation Rules)
    validate_entity_class(entity_class)

    # Extract roles (multi-valued)
    canonical_roles = extract_roles(raw_data)

    # Extract activities
    canonical_activities = extract_activities(raw_data)

    # Extract place types (only for places)
    canonical_place_types = extract_place_types(raw_data) if entity_class == "place" else []

    # Events typically have no roles (see classification_rules.md - Example 6)
    if entity_class == "event":
        canonical_roles = []

    return {
        "entity_class": entity_class,
        "canonical_roles": canonical_roles,
        "canonical_activities": canonical_activities,
        "canonical_place_types": canonical_place_types,
    }


def get_engine_modules(entity_class: str) -> List[str]:
    """
    Get required engine modules for a given entity_class.

    This function loads the entity_model.yaml configuration and returns
    the list of required universal modules for the specified entity_class.

    Args:
        entity_class: Entity classification (place, person, organization, event, thing)

    Returns:
        List of required module names (e.g., ["core", "location"])

    Raises:
        AssertionError: If entity_class is not valid
        ValueError: If entity_class is not found in entity_model.yaml

    See: engine/config/entity_model.yaml for module definitions

    Examples:
        >>> get_engine_modules("place")
        ['core', 'location']

        >>> get_engine_modules("person")
        ['core', 'contact']

        >>> get_engine_modules("event")
        ['core', 'time_range']
    """
    import yaml
    import os

    # Validate entity_class
    validate_entity_class(entity_class)

    # Load entity_model.yaml
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "config",
        "entity_model.yaml"
    )

    with open(config_path, "r", encoding="utf-8") as f:
        entity_model = yaml.safe_load(f)

    # Get required modules for entity_class
    entity_classes = entity_model.get("entity_classes", {})
    entity_config = entity_classes.get(entity_class)

    if not entity_config:
        raise ValueError(
            f"Entity class '{entity_class}' not found in entity_model.yaml. "
            f"Available classes: {', '.join(sorted(entity_classes.keys()))}"
        )

    required_modules = entity_config.get("required_modules", [])
    return required_modules
