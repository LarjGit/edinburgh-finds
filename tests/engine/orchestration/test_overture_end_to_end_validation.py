import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.ingestion.connectors.overture_local import OvertureLocalConnector
from engine.orchestration.cli import bootstrap_lens
from engine.orchestration.execution_plan import ConnectorSpec, ExecutionPhase, ExecutionPlan
from engine.orchestration.planner import orchestrate
from engine.orchestration.types import IngestRequest, IngestionMode
from tests.utils import unwrap_prisma_json


def _build_overture_only_plan() -> ExecutionPlan:
    plan = ExecutionPlan()
    plan.add_connector(
        ConnectorSpec(
            name="overture_local",
            phase=ExecutionPhase.STRUCTURED,
            trust_level=85,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.0,
        )
    )
    return plan


def _write_overture_fixture() -> Path:
    fixture_payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "overture-fixture-001",
                "geometry": {"type": "Point", "coordinates": [-3.1883, 55.9533]},
                "properties": {
                    "name": "Fixture Padel Sports Centre",
                    "category": "sports_centre",
                    "city": "Edinburgh",
                },
            }
        ],
    }
    fixture_dir = Path("engine/data/raw/overture_local")
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = fixture_dir / "overture_fixture_contract.json"
    fixture_path.write_text(json.dumps(fixture_payload), encoding="utf-8")
    return fixture_path


@pytest.mark.asyncio
async def test_overture_fixture_pipeline_persists_entity_with_canonicals_and_module():
    fixture_path = _write_overture_fixture()
    overture_connector = OvertureLocalConnector(fixture_path=str(fixture_path))
    ctx = bootstrap_lens("edinburgh_finds")

    run_created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    captured_entities = []
    raw_rows = {}
    extracted_rows = []

    mock_db = AsyncMock()
    mock_db.connect = AsyncMock()
    mock_db.disconnect = AsyncMock()
    mock_db.is_connected = MagicMock(return_value=True)

    orchestration_run = SimpleNamespace(id="run-overture-fixture", createdAt=run_created_at)
    mock_db.orchestrationrun.create = AsyncMock(return_value=orchestration_run)
    mock_db.orchestrationrun.update = AsyncMock()
    mock_db.orchestrationrun.find_unique = AsyncMock(return_value=orchestration_run)

    mock_db.connectorusage.find_first = AsyncMock(return_value=None)
    mock_db.connectorusage.upsert = AsyncMock()

    async def create_raw_ingestion(*, data):
        raw_id = f"raw-{len(raw_rows) + 1}"
        row = SimpleNamespace(
            id=raw_id,
            source=data["source"],
            file_path=data["file_path"],
            hash=data["hash"],
        )
        raw_rows[raw_id] = row
        return row

    async def find_raw_ingestion(*, where):
        return raw_rows.get(where["id"])

    mock_db.rawingestion.find_first = AsyncMock(return_value=None)
    mock_db.rawingestion.create = AsyncMock(side_effect=create_raw_ingestion)
    mock_db.rawingestion.find_unique = AsyncMock(side_effect=find_raw_ingestion)

    async def create_extracted(*, data):
        extracted = SimpleNamespace(
            id=f"ext-{len(extracted_rows) + 1}",
            source=data["source"],
            entity_class=data["entity_class"],
            attributes=data["attributes"],
            discovered_attributes=data["discovered_attributes"],
            external_ids=data.get("external_ids", "{}"),
            raw_ingestion=raw_rows[data["raw_ingestion_id"]],
            createdAt=run_created_at,
        )
        extracted_rows.append(extracted)
        return extracted

    async def find_extracted(**kwargs):
        del kwargs
        return extracted_rows

    mock_db.extractedentity.create = AsyncMock(side_effect=create_extracted)
    mock_db.extractedentity.find_many = AsyncMock(side_effect=find_extracted)

    mock_db.entity.find_unique = AsyncMock(return_value=None)

    async def create_entity(*, data):
        captured_entities.append(data)
        return SimpleNamespace(id=f"entity-{len(captured_entities)}")

    mock_db.entity.create = AsyncMock(side_effect=create_entity)
    mock_db.entity.update = AsyncMock()

    try:
        with patch("engine.orchestration.planner.Prisma", return_value=mock_db), patch(
            "engine.orchestration.planner.select_connectors",
            return_value=_build_overture_only_plan(),
        ), patch(
            "engine.orchestration.planner.get_connector_instance",
            return_value=overture_connector,
        ):
            request = IngestRequest(
                ingestion_mode=IngestionMode.RESOLVE_ONE,
                query="fixture overture padel edinburgh",
                persist=True,
            )
            report = await orchestrate(request, ctx=ctx)

        assert report["candidates_found"] == 1
        assert report["accepted_entities"] == 1
        assert report["persisted_count"] == 1
        assert report["entities_created"] == 1
        assert report["entities_updated"] == 0
        assert report["persistence_errors"] == []

        assert len(captured_entities) == 1
        entity = unwrap_prisma_json(captured_entities[0])

        assert entity["entity_name"] == "Fixture Padel Sports Centre"
        assert entity["entity_class"] == "place"
        assert entity["canonical_activities"] == ["padel"]
        assert entity["canonical_place_types"] == ["sports_facility"]
        assert entity["modules"]["sports_facility"]["source_signals"]["primary_category"] == "sports_centre"
    finally:
        fixture_path.unlink(missing_ok=True)
