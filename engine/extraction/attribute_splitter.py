"""
Attribute splitting utilities.
"""

from typing import Dict, Optional, Tuple

from engine.extraction.schema_utils import get_extraction_fields


def split_attributes(
    extracted: Dict, entity_type: Optional[object] = None
) -> Tuple[Dict, Dict]:
    """
    Split extracted fields into schema attributes and discovered attributes.
    """
    schema_fields = {field.name for field in get_extraction_fields(entity_type)}
    attributes: Dict = {}
    discovered: Dict = {}

    for key, value in extracted.items():
        if key == "discovered_attributes":
            if isinstance(value, dict):
                discovered.update(value)
            else:
                discovered[key] = value
            continue

        if key in schema_fields:
            attributes[key] = value
        else:
            discovered[key] = value

    return attributes, discovered

