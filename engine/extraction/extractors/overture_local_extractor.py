"""
Overture local extractor.

Phase-1 deterministic extraction for Overture place records. Emits only schema
primitives and raw observations.
"""

from typing import Any, Dict, List, Optional, Tuple

from engine.extraction.base import BaseExtractor
from engine.extraction.schema_utils import is_field_in_schema
from engine.orchestration.execution_context import ExecutionContext


FORBIDDEN_PHASE2_FIELDS = {
    "canonical_activities",
    "canonical_roles",
    "canonical_place_types",
    "canonical_access",
    "modules",
}


class OvertureLocalExtractor(BaseExtractor):
    """Extractor for Overture local connector payloads."""

    @property
    def source_name(self) -> str:
        return "overture_local"

    def extract(self, raw_data: Dict[str, Any], *, ctx: ExecutionContext) -> Dict[str, Any]:
        del ctx  # Extractor remains deterministic and context-agnostic.

        if not isinstance(raw_data, dict):
            raise ValueError("Overture record must be a JSON object")

        if raw_data.get("type") == "FeatureCollection" or "features" in raw_data:
            raise ValueError(
                "Unsupported Overture contract: GeoJSON FeatureCollection wrapper is not accepted; "
                "expected row-style place record"
            )

        extracted: Dict[str, Any] = {}

        entity_name = self._extract_entity_name(raw_data)
        if not entity_name:
            raise ValueError("Overture place row field 'names.primary' (or adapter name) is required")
        extracted["entity_name"] = entity_name

        coordinates = self._extract_point_coordinates(raw_data.get("geometry"))
        if coordinates is not None:
            extracted["longitude"] = coordinates[0]
            extracted["latitude"] = coordinates[1]

        categories = self._extract_categories(raw_data)
        if categories:
            extracted["raw_categories"] = categories

        external_id = raw_data.get("id")
        if external_id is not None:
            extracted["external_id"] = str(external_id)

        source_datasets = self._extract_source_datasets(raw_data.get("sources"))
        if source_datasets:
            extracted["overture_source_datasets"] = source_datasets

        return extracted

    def validate(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        validated = extracted.copy()

        if not validated.get("entity_name"):
            raise ValueError("Missing required field: entity_name")

        forbidden = sorted(field for field in FORBIDDEN_PHASE2_FIELDS if field in validated)
        if forbidden:
            raise ValueError(
                "Extraction Boundary violation: Phase 1 extractor emitted forbidden fields: "
                + ", ".join(forbidden)
            )

        latitude = validated.get("latitude")
        if latitude is not None and (latitude < -90 or latitude > 90):
            validated.pop("latitude", None)

        longitude = validated.get("longitude")
        if longitude is not None and (longitude < -180 or longitude > 180):
            validated.pop("longitude", None)

        if isinstance(validated.get("raw_categories"), list):
            validated["raw_categories"] = self._dedupe_strings(validated["raw_categories"])

        return validated

    def split_attributes(self, extracted: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        attributes: Dict[str, Any] = {}
        discovered: Dict[str, Any] = {}

        for key, value in extracted.items():
            if is_field_in_schema(key):
                attributes[key] = value
            else:
                discovered[key] = value

        return attributes, discovered

    def _extract_entity_name(self, raw_data: Dict[str, Any]) -> Optional[str]:
        if isinstance(raw_data.get("name"), str) and raw_data["name"].strip():
            return raw_data["name"].strip()

        names = raw_data.get("names")
        if isinstance(names, dict):
            primary_name = names.get("primary")
            if isinstance(primary_name, str) and primary_name.strip():
                return primary_name.strip()
            if isinstance(primary_name, dict):
                value = primary_name.get("value")
                if isinstance(value, str) and value.strip():
                    return value.strip()

        properties = raw_data.get("properties")
        if isinstance(properties, dict):
            prop_name = properties.get("name")
            if isinstance(prop_name, str) and prop_name.strip():
                return prop_name.strip()

        return None

    def _extract_categories(self, raw_data: Dict[str, Any]) -> List[str]:
        values: List[str] = []

        categories = raw_data.get("categories")
        if isinstance(categories, dict):
            primary = categories.get("primary")
            if isinstance(primary, str):
                values.append(primary)
            alternate = categories.get("alternate")
            if isinstance(alternate, str):
                values.append(alternate)
            elif isinstance(alternate, list):
                values.extend(item for item in alternate if isinstance(item, str))

        properties = raw_data.get("properties")
        if isinstance(properties, dict):
            category = properties.get("category")
            if isinstance(category, str):
                values.append(category)

        return self._dedupe_strings(values)

    def _extract_point_coordinates(self, geometry: Any) -> Optional[Tuple[float, float]]:
        if not isinstance(geometry, dict):
            return None

        if geometry.get("type") != "Point":
            return None

        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            return None

        try:
            longitude = float(coordinates[0])
            latitude = float(coordinates[1])
        except (TypeError, ValueError):
            return None

        return longitude, latitude

    def _extract_source_datasets(self, sources: Any) -> List[str]:
        if not isinstance(sources, list):
            return []

        datasets = [
            source.get("dataset")
            for source in sources
            if isinstance(source, dict) and isinstance(source.get("dataset"), str)
        ]
        return self._dedupe_strings(datasets)

    def _dedupe_strings(self, values: List[str]) -> List[str]:
        deduped: List[str] = []
        seen = set()
        for value in values:
            if not isinstance(value, str):
                continue
            cleaned = value.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            deduped.append(cleaned)
        return deduped
