import json
from pathlib import Path
from unittest.mock import patch

import pytest

from engine.ingestion.connectors.overture_local import OvertureLocalConnector


def _fixture_path() -> Path:
    return Path(__file__).parents[3] / "fixtures" / "overture" / "overture_feature_collection.json"


@pytest.mark.asyncio
async def test_fetch_returns_results_for_valid_feature_collection():
    connector = OvertureLocalConnector(fixture_path=str(_fixture_path()))

    payload = await connector.fetch("ignored query")

    assert "results" in payload
    assert len(payload["results"]) == 2
    assert payload["results"][0]["name"] == "Overture Test Venue One"
    assert payload["results"][1]["name"] == "Overture Test Venue Two"


@pytest.mark.asyncio
async def test_fetch_rejects_non_feature_collection_payload():
    connector = OvertureLocalConnector(fixture_path=str(_fixture_path()))
    invalid_payload = json.dumps({"type": "NotAFeatureCollection", "features": []})

    with patch.object(Path, "read_text", return_value=invalid_payload):
        with pytest.raises(ValueError, match="FeatureCollection"):
            await connector.fetch("ignored query")
