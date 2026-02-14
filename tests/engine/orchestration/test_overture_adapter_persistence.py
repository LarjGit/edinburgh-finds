import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from engine.ingestion.connectors.overture_local import OvertureLocalConnector
from engine.orchestration.adapters import ConnectorAdapter
from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.execution_plan import ConnectorSpec, ExecutionPhase
from engine.orchestration.orchestrator_state import OrchestratorState
from engine.orchestration.persistence import PersistenceManager
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.types import IngestRequest, IngestionMode


def _fixture_path() -> Path:
    return Path(__file__).parents[2] / "fixtures" / "overture" / "overture_feature_collection.json"


@pytest.mark.asyncio
async def test_overture_adapter_path_persists_raw_ingestion_even_when_extraction_fails():
    connector = OvertureLocalConnector(fixture_path=str(_fixture_path()))
    spec = ConnectorSpec(
        name="overture_local",
        phase=ExecutionPhase.STRUCTURED,
        trust_level=85,
        requires=["request.query"],
        provides=["context.candidates"],
        supports_query_only=True,
        estimated_cost_usd=0.0,
    )
    adapter = ConnectorAdapter(connector, spec)
    context = ExecutionContext(
        lens_id="edinburgh_finds",
        lens_contract={
            "mapping_rules": [],
            "module_triggers": [],
            "modules": {},
            "facets": {},
            "values": [],
            "confidence_threshold": 0.7,
        },
        lens_hash="test_hash",
    )
    state = OrchestratorState()
    request = IngestRequest(
        ingestion_mode=IngestionMode.DISCOVER_MANY,
        query="overture test venues",
    )
    query_features = QueryFeatures.extract(
        query=request.query,
        request=request,
        lens_name="edinburgh_finds",
    )

    await adapter.execute(request, query_features, context, state)
    assert len(state.candidates) == 2

    for candidate in state.candidates:
        state.accept_entity(candidate)
    assert len(state.accepted_entities) >= 1

    async def create_raw_ingestion(*, data):
        row = Mock()
        row.id = f"raw-{len(created_raw_rows) + 1}"
        row.source = data["source"]
        row.status = data["status"]
        row.hash = data["hash"]
        row.metadata_json = data["metadata_json"]
        row.file_path = data["file_path"]
        created_raw_rows.append(row)
        return row

    created_raw_rows = []
    mock_db = Mock()
    mock_db.rawingestion = Mock()
    mock_db.rawingestion.find_first = AsyncMock(return_value=None)
    mock_db.rawingestion.create = AsyncMock(side_effect=create_raw_ingestion)
    mock_db.extractedentity = Mock()
    mock_db.extractedentity.create = AsyncMock()

    errors = []
    with patch(
        "engine.orchestration.persistence.extract_entity",
        side_effect=ValueError("No extractor found for source: overture_local"),
    ), patch("engine.orchestration.persistence.Path.write_text", return_value=0):
        manager = PersistenceManager(db=mock_db)
        result = await manager.persist_entities(state.accepted_entities, errors)

    accepted_count = len(state.accepted_entities)
    assert result["persisted_count"] == 0
    assert len(result["persistence_errors"]) == accepted_count
    assert len(errors) == accepted_count

    assert mock_db.rawingestion.create.await_count == accepted_count
    assert mock_db.extractedentity.create.await_count == 0

    for candidate, call in zip(state.accepted_entities, mock_db.rawingestion.create.call_args_list):
        raw_ingestion_data = call.kwargs["data"]
        expected_hash = hashlib.sha256(
            json.dumps(candidate["raw"], indent=2).encode()
        ).hexdigest()[:16]

        assert raw_ingestion_data["source"] == "overture_local"
        assert raw_ingestion_data["status"] == "success"
        assert raw_ingestion_data["hash"] == expected_hash

        metadata = json.loads(raw_ingestion_data["metadata_json"])
        assert metadata["ingestion_mode"] == "orchestration"
        assert metadata["candidate_name"] == candidate["name"]
