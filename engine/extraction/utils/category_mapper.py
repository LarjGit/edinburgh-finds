"""
Category Mapper - Map raw categories to canonical taxonomy

This module provides functionality to map raw, uncontrolled categories
(extracted from various sources) to a controlled canonical taxonomy defined
in canonical_categories.yaml.

Features:
- Load taxonomy and mapping rules from config
- Apply regex-based pattern matching to raw categories
- Return canonical categories based on confidence threshold
- Log unmapped categories for manual review
- Support for multi-label classification (one raw category -> multiple canonical)

Example:
    >>> from engine.extraction.utils.category_mapper import map_to_canonical
    >>> raw_categories = ["Tennis Club", "Indoor Sports Facility"]
    >>> canonical = map_to_canonical(raw_categories)
    >>> print(canonical)
    ['tennis', 'sports_centre']
"""

import re
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Cache for config (loaded once per process)
_config_cache: Optional[Dict] = None


def load_config() -> Dict:
    """
    Load canonical categories configuration from YAML file.

    Returns:
        Dict: Configuration containing taxonomy, mapping_rules, and promotion_config

    Raises:
        FileNotFoundError: If canonical_categories.yaml is not found
        yaml.YAMLError: If YAML file is malformed
    """
    global _config_cache

    # Return cached config if available
    if _config_cache is not None:
        return _config_cache

    # Find config file (relative to this module)
    config_path = Path(__file__).parent.parent.parent / "config" / "canonical_categories.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Canonical categories config not found: {config_path}")

    # Load YAML
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Validate required sections
    required_keys = ['taxonomy', 'mapping_rules', 'promotion_config']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required section in canonical_categories.yaml: {key}")

    # Cache for future calls
    _config_cache = config

    logger.info(
        f"Loaded canonical categories config: "
        f"{len(config['taxonomy'])} categories, "
        f"{len(config['mapping_rules'])} mapping rules"
    )

    return config


def get_taxonomy() -> List[Dict]:
    """
    Get the canonical taxonomy list.

    Returns:
        List[Dict]: List of canonical category definitions
    """
    config = load_config()
    return config['taxonomy']


def get_category_keys() -> Set[str]:
    """
    Get all valid canonical category keys.

    Returns:
        Set[str]: Set of category_key values from taxonomy
    """
    taxonomy = get_taxonomy()
    return {cat['category_key'] for cat in taxonomy}


def map_to_canonical(
    raw_categories: Optional[List[str]],
    min_confidence: Optional[float] = None,
    log_unmapped: Optional[bool] = None
) -> List[str]:
    """
    Map raw categories to canonical categories using configured rules.

    This function:
    1. Loads mapping rules from config
    2. Applies pattern matching to each raw category
    3. Collects canonical categories that meet confidence threshold
    4. Returns unique list of canonical categories
    5. Logs unmapped categories if configured

    Args:
        raw_categories: List of raw category strings from extraction
        min_confidence: Minimum confidence threshold (overrides config default)
        log_unmapped: Whether to log unmapped categories (overrides config default)

    Returns:
        List[str]: List of canonical category keys

    Example:
        >>> map_to_canonical(["Tennis Club", "Private Members"])
        ['tennis', 'private_club']

        >>> map_to_canonical(["Some Random Category"])
        []  # No matches above confidence threshold
    """
    if not raw_categories:
        return []

    # Load config
    config = load_config()
    mapping_rules = config['mapping_rules']
    promotion_config = config['promotion_config']

    # Use provided values or fall back to config defaults
    min_conf = min_confidence if min_confidence is not None else promotion_config['min_confidence']
    should_log_unmapped = log_unmapped if log_unmapped is not None else promotion_config['log_unmapped']
    max_cats = promotion_config['max_categories']

    # Track which raw categories were mapped
    mapped_raw_categories = set()
    canonical_categories = set()

    # Apply mapping rules to each raw category
    for raw_cat in raw_categories:
        if not raw_cat or not isinstance(raw_cat, str):
            continue

        raw_cat = raw_cat.strip()
        if not raw_cat:
            continue

        # Try each mapping rule
        for rule in mapping_rules:
            pattern = rule['pattern']
            canonical_key = rule['canonical']
            confidence = rule['confidence']

            # Skip if confidence too low
            if confidence < min_conf:
                continue

            # Apply regex match
            if re.search(pattern, raw_cat):
                canonical_categories.add(canonical_key)
                mapped_raw_categories.add(raw_cat)
                logger.debug(
                    f"Mapped '{raw_cat}' -> '{canonical_key}' "
                    f"(confidence: {confidence}, pattern: {pattern})"
                )
                # Note: We don't break here - one raw category can match multiple rules

    # Log unmapped categories
    if should_log_unmapped:
        unmapped = set(raw_categories) - mapped_raw_categories
        for raw_cat in unmapped:
            if raw_cat and isinstance(raw_cat, str) and raw_cat.strip():
                _log_unmapped_category(raw_cat.strip())

    # Convert to list and limit to max_categories
    result = list(canonical_categories)[:max_cats]

    logger.info(
        f"Mapped {len(raw_categories)} raw categories -> "
        f"{len(result)} canonical categories"
    )

    return result


def map_single_category(raw_category: str, min_confidence: float = 0.7) -> List[Tuple[str, float]]:
    """
    Map a single raw category to canonical categories with confidence scores.

    Useful for debugging and manual review workflows.

    Args:
        raw_category: Single raw category string
        min_confidence: Minimum confidence threshold

    Returns:
        List[Tuple[str, float]]: List of (canonical_key, confidence) tuples
                                 sorted by confidence (highest first)

    Example:
        >>> map_single_category("Indoor Tennis Club")
        [('tennis', 1.0), ('sports_centre', 0.85)]
    """
    if not raw_category or not isinstance(raw_category, str):
        return []

    config = load_config()
    mapping_rules = config['mapping_rules']

    matches = []

    for rule in mapping_rules:
        pattern = rule['pattern']
        canonical_key = rule['canonical']
        confidence = rule['confidence']

        if confidence < min_confidence:
            continue

        if re.search(pattern, raw_category):
            matches.append((canonical_key, confidence))

    # Sort by confidence (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)

    return matches


def validate_canonical_categories(categories: List[str]) -> Tuple[List[str], List[str]]:
    """
    Validate that all categories are in the canonical taxonomy.

    Args:
        categories: List of category keys to validate

    Returns:
        Tuple[List[str], List[str]]: (valid_categories, invalid_categories)

    Example:
        >>> validate_canonical_categories(['tennis', 'padel', 'invalid_cat'])
        (['tennis', 'padel'], ['invalid_cat'])
    """
    valid_keys = get_category_keys()
    valid = []
    invalid = []

    for cat in categories:
        if cat in valid_keys:
            valid.append(cat)
        else:
            invalid.append(cat)

    return valid, invalid


def get_category_display_name(category_key: str) -> Optional[str]:
    """
    Get the user-facing display name for a canonical category.

    Args:
        category_key: Canonical category key

    Returns:
        str: Display name, or None if category not found

    Example:
        >>> get_category_display_name('sports_centre')
        'Sports Centre'
    """
    taxonomy = get_taxonomy()

    for cat in taxonomy:
        if cat['category_key'] == category_key:
            return cat['display_name']

    return None


def _log_unmapped_category(raw_category: str):
    """
    Log an unmapped category for manual review.

    Logs to both the standard logger and optionally to a file.

    Args:
        raw_category: The raw category that wasn't mapped
    """
    config = load_config()
    promotion_config = config['promotion_config']

    # Log to standard logger
    logger.info(f"Unmapped category: '{raw_category}'")

    # Log to file if configured
    if 'unmapped_log_path' in promotion_config:
        log_path = Path(promotion_config['unmapped_log_path'])

        # Create log directory if it doesn't exist
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Append to log file
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"{raw_category}\n")
        except IOError as e:
            logger.warning(f"Failed to write to unmapped categories log: {e}")


def reload_config():
    """
    Force reload of the canonical categories configuration.

    Useful for testing or when config changes at runtime.
    """
    global _config_cache
    _config_cache = None
    load_config()
