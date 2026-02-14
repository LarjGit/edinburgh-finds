"""
Local-file Overture connector for Tier 1 onboarding slices.

This connector is intentionally offline-only. It reads a local GeoJSON
FeatureCollection fixture and emits adapter-compatible results.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.ingestion.base import BaseConnector


class OvertureLocalConnector(BaseConnector):
    """Read Overture features from a local FeatureCollection JSON file."""

    def __init__(self, fixture_path: Optional[str] = None):
        self.fixture_path = Path(
            fixture_path or "tests/fixtures/overture/overture_feature_collection.json"
        )

    @property
    def source_name(self) -> str:
        return "overture_local"

    async def fetch(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        del query  # Local fixture connector ignores query text by design.

        payload = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        if payload.get("type") != "FeatureCollection":
            raise ValueError("Overture fixture must be a GeoJSON FeatureCollection")

        features = payload.get("features")
        if not isinstance(features, list):
            raise ValueError("Overture FeatureCollection must include a features list")

        return {"results": [self._feature_to_result(feature) for feature in features]}

    def _feature_to_result(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        properties = feature.get("properties", {})
        name = properties.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Each Overture feature must provide properties.name")

        return {
            "name": name.strip(),
            "id": feature.get("id"),
            "geometry": feature.get("geometry"),
            "properties": properties,
            "type": feature.get("type", "Feature"),
        }

    async def save(self, data: dict, source_url: str) -> str:
        raise NotImplementedError(
            "OvertureLocalConnector.save() is not used in orchestration adapter flow"
        )

    async def is_duplicate(self, content_hash: str) -> bool:
        raise NotImplementedError(
            "OvertureLocalConnector.is_duplicate() is not used in adapter flow"
        )
