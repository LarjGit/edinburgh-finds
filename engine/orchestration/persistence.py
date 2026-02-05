"""
Persistence layer for orchestration system.

Handles saving accepted entities to the database after cross-source deduplication.
Uses the existing ExtractedEntity model from the extraction system.
"""

import asyncio
import hashlib
import json
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from prisma import Prisma

from engine.orchestration.extraction_integration import extract_entity
from engine.ingestion.deduplication import check_duplicate

# Set up structured logging with prefix
logger = logging.getLogger(__name__)


class PersistenceManager:
    """
    Manages persistence of accepted entities to the database.

    Converts canonical candidate format to ExtractedEntity records
    and handles database operations with error handling.
    """

    def __init__(self, db: Optional[Prisma] = None):
        """
        Initialize persistence manager.

        Args:
            db: Prisma database client (optional, will create if not provided)
        """
        self.db = db
        self._db_created = False

    async def __aenter__(self):
        """Async context manager entry - connect to database."""
        if self.db is None:
            self.db = Prisma()
            self._db_created = True

        if not self.db.is_connected():
            await self.db.connect()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - disconnect from database."""
        if self._db_created and self.db is not None:
            await self.db.disconnect()

    async def persist_entities(
        self,
        accepted_entities: List[Dict[str, Any]],
        errors: List[Dict[str, Any]],
        orchestration_run_id: Optional[str] = None,
        context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Persist accepted entities to the database.

        Creates RawIngestion records first to maintain data lineage,
        then creates linked ExtractedEntity records.

        Args:
            accepted_entities: List of accepted (deduplicated) candidate dicts
            errors: List to append persistence errors to
            orchestration_run_id: Optional ID of OrchestrationRun to link RawIngestions to
            context: Optional ExecutionContext with lens contract

        Returns:
            Dict with persistence statistics:
            - persisted_count: Number of entities successfully saved
            - persistence_errors: List of errors that occurred
        """
        persisted_count = 0
        persistence_errors = []

        for candidate in accepted_entities:
            try:
                # Step 1: Save raw payload to disk (like ingestion system)
                source = candidate.get("source", "orchestration")
                candidate_name = candidate.get("name", "unknown")
                raw_item = candidate.get("raw", {})

                # Create directory structure: engine/data/raw/<source>/
                data_dir = Path("engine/data/raw") / source
                data_dir.mkdir(parents=True, exist_ok=True)

                # Generate content hash for deduplication
                raw_payload_str = json.dumps(raw_item, indent=2)
                content_hash = hashlib.sha256(raw_payload_str.encode()).hexdigest()[:16]

                # Step 2: Check for duplicate (RI-001: Ingestion-level deduplication)
                is_duplicate = await check_duplicate(self.db, content_hash)

                if is_duplicate:
                    # Reuse existing RawIngestion record (RI-002: Replay stability)
                    raw_ingestion = await self.db.rawingestion.find_first(
                        where={"hash": content_hash}
                    )
                    logger.debug(
                        f"[PERSIST] Duplicate payload detected for source={source}, "
                        f"reusing existing raw_ingestion_id={raw_ingestion.id}, hash={content_hash}"
                    )
                else:
                    # New payload - save to disk and create RawIngestion record
                    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    file_name = f"{timestamp}_{content_hash}.json"
                    file_path = data_dir / file_name

                    # Write raw payload to disk
                    file_path.write_text(raw_payload_str, encoding="utf-8")

                    # Generate source URL from raw item (connector-specific)
                    source_url = self._extract_source_url(raw_item, source, candidate_name)

                    # Create RawIngestion record
                    raw_ingestion_data = {
                        "source": source,
                        "source_url": source_url,
                        "file_path": str(file_path.relative_to(Path("."))),  # Relative path from project root
                        "status": "success",
                        "hash": content_hash,
                        "metadata_json": json.dumps({
                            "ingestion_mode": "orchestration",
                            "candidate_name": candidate_name,
                        }),
                    }

                    # Link to OrchestrationRun if provided
                    if orchestration_run_id:
                        raw_ingestion_data["orchestration_run_id"] = orchestration_run_id

                    raw_ingestion = await self.db.rawingestion.create(data=raw_ingestion_data)

                    logger.debug(
                        f"[PERSIST] Created new RawIngestion: source={source}, "
                        f"raw_ingestion_id={raw_ingestion.id}, hash={content_hash}"
                    )

                # Step 3: Extract entity with full pipeline (Phase 1 + Phase 2 lens application)
                # All sources go through extract_entity() to ensure lens application happens
                # (LA-003 fix: structured sources need lens enrichment too)
                logger.debug(
                    f"[PERSIST] Extracting entity from source={source}, "
                    f"raw_ingestion_id={raw_ingestion.id}, entity_name={candidate_name}"
                )

                # Use extraction engine to properly extract and structure the data
                extracted_data = await extract_entity(raw_ingestion.id, self.db, context)

                # Log extraction success with details
                entity_class = extracted_data["entity_class"]
                attr_count = len(extracted_data.get("attributes", {}))
                logger.debug(
                    f"[PERSIST] Successfully extracted entity: entity_class={entity_class}, "
                    f"attributes={attr_count}, raw_ingestion_id={raw_ingestion.id}"
                )

                # Build entity_data from extraction result
                entity_data = {
                    "source": source,
                    "entity_class": extracted_data["entity_class"],
                    "attributes": json.dumps(extracted_data["attributes"]),
                    "discovered_attributes": json.dumps(extracted_data["discovered_attributes"]),
                    "raw_ingestion_id": raw_ingestion.id,
                }

                # Add optional fields if present
                if "external_ids" in extracted_data:
                    entity_data["external_ids"] = json.dumps(extracted_data["external_ids"])

                if "model_used" in extracted_data:
                    entity_data["model_used"] = extracted_data["model_used"]

                # Step 4: Create ExtractedEntity record
                await self.db.extractedentity.create(data=entity_data)

                persisted_count += 1

            except Exception as e:
                # Log error with full context and stack trace
                source = candidate.get("source", "unknown")
                name = candidate.get("name", "unknown")
                error_msg = f"Failed to persist entity from {source}: {str(e)}"

                logger.error(
                    f"[PERSIST] Extraction failed: source={source}, entity_name={name}, "
                    f"raw_ingestion_id={raw_ingestion.id if 'raw_ingestion' in locals() else 'N/A'}, "
                    f"error={str(e)}",
                    exc_info=True  # This includes the full stack trace
                )

                persistence_errors.append({
                    "source": source,
                    "error": error_msg,
                    "entity_name": name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                # Also append to main errors list
                errors.append({
                    "connector": source,
                    "error": error_msg,
                })

        return {
            "persisted_count": persisted_count,
            "persistence_errors": persistence_errors,
        }

    def _extract_source_url(self, raw_item: Dict[str, Any], source: str, fallback_name: str) -> str:
        """
        Extract the original source URL from raw API response.

        Args:
            raw_item: Raw API response dict
            source: Source connector name
            fallback_name: Fallback name if URL can't be extracted

        Returns:
            Source URL string
        """
        if source == "serper":
            return raw_item.get("link", f"https://www.google.com/search?q={fallback_name}")
        elif source == "google_places":
            # Google Places API doesn't provide a direct URL, use Maps link
            place_id = raw_item.get("place_id") or raw_item.get("id")
            if place_id:
                return f"https://www.google.com/maps/place/?q=place_id:{place_id}"
            return f"https://www.google.com/maps/search/{fallback_name}"
        elif source == "openstreetmap":
            osm_type = raw_item.get("type", "node")
            osm_id = raw_item.get("id", "unknown")
            return f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
        elif source == "sport_scotland":
            return raw_item.get("properties", {}).get("url", f"https://www.activeplaces.com/search?q={fallback_name}")
        else:
            return f"orchestration://{source}/{fallback_name}"


def get_db_client() -> Prisma:
    """
    Factory function to get database client.

    Used for dependency injection in tests.

    Returns:
        Prisma database client
    """
    return Prisma()


def persist_entities_sync(
    accepted_entities: List[Dict[str, Any]], errors: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Synchronous wrapper for persistence operations.

    Handles event loop detection and runs async operations appropriately.

    Args:
        accepted_entities: List of accepted candidate dicts
        errors: List to append errors to

    Returns:
        Dict with persisted_count and persistence_errors
    """
    # Check if we're in an event loop
    try:
        loop = asyncio.get_running_loop()
        # Already in event loop - cannot use asyncio.run()
        # This happens in tests - return empty result
        return {
            "persisted_count": 0,
            "persistence_errors": [{
                "source": "persistence",
                "error": "Cannot persist from within async context",
                "entity_name": "N/A",
            }],
        }
    except RuntimeError:
        # No event loop - safe to use asyncio.run()
        return asyncio.run(_persist_async(accepted_entities, errors))


async def _persist_async(accepted_entities, errors):
    """
    Internal async helper for persistence.

    Args:
        accepted_entities: List of accepted candidates
        errors: List to append errors to

    Returns:
        Dict with persisted_count and persistence_errors
    """
    async with PersistenceManager() as persistence:
        return await persistence.persist_entities(accepted_entities, errors)
