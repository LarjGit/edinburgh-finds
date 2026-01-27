"""
Persistence layer for orchestration system.

Handles saving accepted entities to the database after cross-source deduplication.
Uses the existing ExtractedEntity model from the extraction system.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from prisma import Prisma


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
        self, accepted_entities: List[Dict[str, Any]], errors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Persist accepted entities to the database.

        Args:
            accepted_entities: List of accepted (deduplicated) candidate dicts
            errors: List to append persistence errors to

        Returns:
            Dict with persistence statistics:
            - persisted_count: Number of entities successfully saved
            - persistence_errors: List of errors that occurred
        """
        persisted_count = 0
        persistence_errors = []

        for candidate in accepted_entities:
            try:
                # Convert candidate to ExtractedEntity format
                entity_data = self._candidate_to_entity_data(candidate)

                # Create ExtractedEntity record
                await self.db.extractedentity.create(data=entity_data)

                persisted_count += 1

            except Exception as e:
                # Log error and continue with next entity
                source = candidate.get("source", "unknown")
                name = candidate.get("name", "unknown")
                error_msg = f"Failed to persist entity from {source}: {str(e)}"
                persistence_errors.append({
                    "source": source,
                    "error": error_msg,
                    "entity_name": name,
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

    def _candidate_to_entity_data(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert canonical candidate format to ExtractedEntity data structure.

        Args:
            candidate: Candidate dict to convert

        Returns:
            Dict suitable for ExtractedEntity.create()
        """
        # Build attributes dict from candidate fields
        attributes = {}

        # Add fields if present
        if "name" in candidate:
            attributes["name"] = candidate["name"]

        if "lat" in candidate and candidate["lat"] is not None:
            attributes["latitude"] = candidate["lat"]

        if "lng" in candidate and candidate["lng"] is not None:
            attributes["longitude"] = candidate["lng"]

        if "address" in candidate and candidate["address"]:
            attributes["address"] = candidate["address"]

        if "phone" in candidate and candidate["phone"]:
            attributes["phone"] = candidate["phone"]

        if "website" in candidate and candidate["website"]:
            attributes["website"] = candidate["website"]

        # Build external_ids dict
        external_ids = {}
        if "ids" in candidate and candidate["ids"]:
            # Copy all IDs from candidate
            external_ids = candidate["ids"].copy()

        # Determine entity_class (default to "place" for now)
        # In future, this could be extracted from candidate metadata
        entity_class = "place"

        # Get source from candidate
        source = candidate.get("source", "orchestration")

        # Build entity data for database
        entity_data = {
            "source": source,
            "entity_class": entity_class,
            "attributes": json.dumps(attributes),
            "external_ids": json.dumps(external_ids),
            "discovered_attributes": json.dumps({}),  # No discovered attributes in orchestration
            "raw_ingestion_id": None,  # Not linked to RawIngestion (orchestration creates entities directly)
        }

        return entity_data


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
