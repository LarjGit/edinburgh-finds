import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from prisma import Prisma

from engine.extraction.extractors.overture_local_extractor import OvertureLocalExtractor
from engine.extraction.run import get_extractor_for_source as resolve_extractor
from engine.ingestion.connectors.overture_release import OvertureReleaseConnector
from engine.orchestration.cli import bootstrap_lens
from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.execution_plan import ConnectorSpec, ExecutionPhase, ExecutionPlan
from engine.orchestration.planner import orchestrate
from engine.orchestration.types import IngestRequest, IngestionMode
from tests.utils import unwrap_prisma_json


def _build_overture_release_only_plan() -> ExecutionPlan:
    plan = ExecutionPlan()
    plan.add_connector(
        ConnectorSpec(
            name="overture_release",
            phase=ExecutionPhase.STRUCTURED,
            trust_level=85,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.0,
        )
    )
    return plan


def _patched_context_for_overture_release(base_ctx: ExecutionContext) -> ExecutionContext:
    lens_contract = deepcopy(base_ctx.lens_contract)
    modules = lens_contract.get("modules", {})

    for module_def in modules.values():
        for rule in module_def.get("field_rules", []):
            applicability = rule.get("applicability")
            if not isinstance(applicability, dict):
                continue
            sources = applicability.get("source")
            if (
                isinstance(sources, list)
                and "overture_local" in sources
                and "overture_release" not in sources
            ):
                applicability["source"] = [*sources, "overture_release"]

    return ExecutionContext(
        lens_id=base_ctx.lens_id,
        lens_contract=lens_contract,
        lens_hash=base_ctx.lens_hash,
    )


def _extractor_with_overture_release_support(source: str):
    if source == "overture_release":
        return OvertureLocalExtractor()
    return resolve_extractor(source)


def _is_sports_signal_row(row: Dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return False

    tokens: List[str] = []
    name = row.get("name")
    if isinstance(name, str):
        tokens.append(name.lower())

    names = row.get("names")
    if isinstance(names, dict):
        primary = names.get("primary")
        if isinstance(primary, str):
            tokens.append(primary.lower())
        elif isinstance(primary, dict):
            value = primary.get("value")
            if isinstance(value, str):
                tokens.append(value.lower())

    categories = row.get("categories")
    if isinstance(categories, dict):
        primary_category = categories.get("primary")
        if isinstance(primary_category, str):
            tokens.append(primary_category.lower())
        alternates = categories.get("alternate")
        if isinstance(alternates, list):
            tokens.extend(
                token.lower() for token in alternates if isinstance(token, str)
            )

    signals = (
        "padel",
        "sports_centre",
        "sports_center",
        "sports centre",
        "sports center",
        "sports facility",
        "sports club",
        "leisure centre",
        "leisure center",
    )
    return any(any(signal in token for signal in signals) for token in tokens)


def _has_populated_module_field(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_populated_module_field(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_populated_module_field(v) for v in value)
    return value not in (None, "", False)


@pytest.mark.slow
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not configured",
)
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_OVERTURE_E2E") != "1",
    reason="Set RUN_LIVE_OVERTURE_E2E=1 to enable live Overture DB proof",
)
async def test_overture_live_single_run_persists_entity_with_canonicals_and_module():
    db = Prisma()
    await db.connect()

    try:
        query = f"overture live e2e {datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            query=query,
            persist=True,
        )
        ctx = _patched_context_for_overture_release(bootstrap_lens("edinburgh_finds"))

        connector = OvertureReleaseConnector(
            timeout_seconds=int(os.getenv("OVERTURE_LIVE_TIMEOUT_SECONDS", "90")),
            max_artifact_size_bytes=int(
                os.getenv("OVERTURE_LIVE_MAX_ARTIFACT_BYTES", str(1024 * 1024 * 1024))
            ),
        )

        original_fetch = connector.fetch

        async def fetch_single_row(query_text: str):
            payload = await original_fetch(query_text)
            rows = payload.get("results", [])
            if not rows:
                return {"results": []}
            sports_row = next((row for row in rows if _is_sports_signal_row(row)), None)
            return {"results": [sports_row or rows[0]]}

        connector.fetch = fetch_single_row

        with patch(
            "engine.orchestration.planner.select_connectors",
            return_value=_build_overture_release_only_plan(),
        ), patch(
            "engine.orchestration.planner.get_connector_instance",
            return_value=connector,
        ), patch(
            "engine.orchestration.extraction_integration.get_extractor_for_source",
            side_effect=_extractor_with_overture_release_support,
        ):
            report = await orchestrate(request, ctx=ctx)

        assert report["persisted_count"] >= 1
        assert report["entities_created"] + report["entities_updated"] >= 1
        assert report["persistence_errors"] == []

        extracted_rows = await db.extractedentity.find_many(
            where={
                "source": "overture_release",
                "createdAt": {"gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)},
            },
            order={"createdAt": "desc"},
            take=1,
        )
        assert extracted_rows, "Expected at least one overture_release extracted row today"

        attributes = json.loads(extracted_rows[0].attributes or "{}")
        entity_name = attributes.get("entity_name")
        assert entity_name, "Expected extracted attributes to include entity_name"

        entity = await db.entity.find_first(
            where={"entity_name": entity_name},
            order={"updatedAt": "desc"},
        )
        assert entity is not None, "Expected persisted Entity row for live Overture result"
        assert entity.entity_name, "Expected non-empty entity_name"

        canonical_activities = entity.canonical_activities or []
        canonical_place_types = entity.canonical_place_types or []
        canonical_roles = entity.canonical_roles or []
        canonical_access = entity.canonical_access or []
        assert any(
            [canonical_activities, canonical_place_types, canonical_roles, canonical_access]
        ), "Expected at least one non-empty canonical dimension"
        assert canonical_place_types, "Expected non-empty canonical_place_types for sports-signaled row"

        modules = unwrap_prisma_json(entity.modules) or {}
        assert isinstance(modules, dict), "Expected modules JSON object"
        assert _has_populated_module_field(modules), "Expected at least one populated modules.* field"

        has_geo = entity.latitude is not None and entity.longitude is not None
        has_address = any([entity.street_address, entity.city, entity.postcode])
        assert has_geo or has_address, "Expected coordinates or address anchor in persisted entity"
    finally:
        await db.disconnect()
