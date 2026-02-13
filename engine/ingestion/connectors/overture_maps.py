"""
Overture Maps Connector.

Provides a minimal Tier 1 baseline connector implementation so Overture Maps
can be selected and executed by orchestration. This slice focuses on connector
queryability and registry/planner integration; extractor behavior is handled in
separate work.
"""

import json
from datetime import datetime
from typing import Any, Dict

import yaml
from prisma import Prisma

from engine.ingestion.base import BaseConnector
from engine.ingestion.deduplication import check_duplicate, compute_content_hash
from engine.ingestion.storage import generate_file_path, save_json


class OvertureMapsConnector(BaseConnector):
    """
    Connector for Overture Maps baseline POI data.

    This implementation is intentionally minimal for Tier 1 queryability:
    it returns a deterministic envelope that can be persisted and processed by
    the orchestration pipeline without requiring live endpoint integration.
    """

    def __init__(self, config_path: str = "engine/config/sources.yaml"):
        """
        Initialize the connector with optional configuration.

        If overture_maps config is missing, defaults are used so factory
        instantiation remains stable in test and development environments.
        """
        config: Dict[str, Any] = {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            config = {}

        overture_config = config.get("overture_maps", {})

        self.base_url = overture_config.get("base_url")
        self.dataset = overture_config.get("dataset", "places")
        self.timeout_seconds = overture_config.get("timeout_seconds", 60)
        self.default_params = overture_config.get("default_params", {})

        self.db = Prisma()

    @property
    def source_name(self) -> str:
        return "overture_maps"

    async def fetch(self, query: str) -> Dict[str, Any]:
        """
        Return a deterministic Overture query envelope.

        Live Overture endpoint fetching is intentionally deferred to a later
        slice; this keeps the connector queryable without adding network
        coupling to this foundational integration task.
        """
        return {
            "source": self.source_name,
            "dataset": self.dataset,
            "query": query,
            "params": dict(self.default_params),
            "items": [],
            "metadata": {
                "base_url_configured": bool(self.base_url),
                "mode": "baseline_queryability",
            },
        }

    async def save(self, data: Dict[str, Any], source_url: str) -> str:
        content_hash = compute_content_hash(data)

        query = str(data.get("query", "unknown"))
        query_slug = query.replace(" ", "_").replace("/", "_")[:50]

        record_id = f"{query_slug}_{content_hash[:8]}"
        file_path = generate_file_path(self.source_name, record_id)
        save_json(file_path, data)

        metadata = {
            "query": query,
            "dataset": data.get("dataset", self.dataset),
            "item_count": len(data.get("items", [])),
        }

        await self.db.rawingestion.create(
            data={
                "source": self.source_name,
                "source_url": source_url,
                "file_path": file_path,
                "hash": content_hash,
                "status": "success",
                "ingested_at": datetime.now(),
                "metadata_json": json.dumps(metadata),
            }
        )

        return file_path

    async def is_duplicate(self, content_hash: str) -> bool:
        return await check_duplicate(self.db, content_hash)
