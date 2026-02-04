"""Entity Finalization - Bridge from ExtractedEntity to Entity table."""

import json
import logging
from typing import List, Dict, Optional, Any
from prisma import Prisma, Json
from prisma.models import ExtractedEntity
from engine.extraction.deduplication import SlugGenerator

logger = logging.getLogger(__name__)


class EntityFinalizer:
    """Finalize entities from extraction to published Entity records."""

    def __init__(self, db: Prisma):
        self.db = db
        self.slug_generator = SlugGenerator()

    async def finalize_entities(
        self,
        orchestration_run_id: str
    ) -> Dict[str, int]:
        """
        Finalize all ExtractedEntity records for an orchestration run.

        Process:
        1. Load all ExtractedEntity records for this run
        2. Group by deduplication key (slug or external_id)
        3. For each group, create or update Entity
        4. Generate slugs for URLs

        Args:
            orchestration_run_id: OrchestrationRun ID

        Returns:
            Stats dict: {"entities_created": N, "entities_updated": M, "conflicts": K}
        """
        # 1. Get the orchestration run's start time
        orchestration_run = await self.db.orchestrationrun.find_unique(
            where={"id": orchestration_run_id}
        )

        if not orchestration_run:
            return {"entities_created": 0, "entities_updated": 0, "conflicts": 0}

        # 2. Load extracted entities created during or after this orchestration run
        # This handles the case where RawIngestion records are reused (duplicates)
        # but new ExtractedEntity records are still created
        extracted_entities = await self.db.extractedentity.find_many(
            where={
                "createdAt": {
                    "gte": orchestration_run.createdAt
                }
            },
            include={"raw_ingestion": True}
        )

        if not extracted_entities:
            return {"entities_created": 0, "entities_updated": 0, "conflicts": 0}

        # 2. Group by identity
        entity_groups = self._group_by_identity(extracted_entities)

        # 3. Finalize each group
        stats = {"entities_created": 0, "entities_updated": 0, "conflicts": 0}

        for identity_key, group in entity_groups.items():
            finalized_data = await self._finalize_group(group)

            # 4. Upsert to Entity table
            existing = await self.db.entity.find_unique(
                where={"slug": finalized_data["slug"]}
            )

            if existing:
                await self.db.entity.update(
                    where={"id": existing.id},
                    data=finalized_data
                )
                stats["entities_updated"] += 1
            else:
                await self.db.entity.create(data=finalized_data)
                stats["entities_created"] += 1

        return stats

    def _group_by_identity(
        self,
        extracted_entities: List[ExtractedEntity]
    ) -> Dict[str, List[ExtractedEntity]]:
        """Group extracted entities by identity (external_id or slug)."""
        groups = {}

        for entity in extracted_entities:
            # Use slug as identity key (external IDs would need more complex matching)
            attributes = json.loads(entity.attributes)
            name = attributes.get("entity_name", "unknown")
            key = f"slug:{self.slug_generator.generate(name)}"

            if key not in groups:
                groups[key] = []
            groups[key].append(entity)

        return groups

    async def _finalize_group(
        self,
        entity_group: List[ExtractedEntity]
    ) -> Dict[str, Any]:
        """Finalize a group of ExtractedEntity records into Entity data.

        Multi-source merge strategy: first non-null value wins for each scalar
        field.  List fields (canonical_* arrays) use the first non-empty list.
        The first entity in the group is the base; subsequent entities fill any
        remaining None / empty-list slots.
        """
        if len(entity_group) == 1:
            return self._finalize_single(entity_group[0])

        # Collect raw attributes from all entities in group
        all_attributes = []
        for entity in entity_group:
            attrs = json.loads(entity.attributes) if entity.attributes else {}
            all_attributes.append(attrs)

        # Base is first entity's finalized form
        merged = self._finalize_single(entity_group[0])

        # Scalar fields: Entity key → extractor attribute key
        scalar_map = {
            "summary": "summary", "latitude": "latitude", "longitude": "longitude",
            "street_address": "street_address", "city": "city", "postcode": "postcode",
            "country": "country", "phone": "phone", "email": "email",
            "website_url": "website",
        }
        list_fields = [
            "canonical_activities", "canonical_roles",
            "canonical_place_types", "canonical_access",
        ]

        for attrs in all_attributes[1:]:
            # Fill null scalars from later sources
            for entity_key, attr_key in scalar_map.items():
                if merged.get(entity_key) is None and attrs.get(attr_key) is not None:
                    merged[entity_key] = attrs[attr_key]

            # Fill empty list fields from later sources
            for field in list_fields:
                if not merged.get(field) and attrs.get(field):
                    merged[field] = attrs[field]

            # Fill missing module keys from later sources
            candidate_modules = attrs.get("modules", {})
            if candidate_modules:
                base_modules = all_attributes[0].get("modules", {})
                for key, value in candidate_modules.items():
                    if key not in base_modules:
                        base_modules[key] = value
                merged["modules"] = Json(base_modules)

        return merged

    def _finalize_single(self, extracted: ExtractedEntity) -> Dict[str, Any]:
        """Convert single ExtractedEntity to Entity format."""
        attributes = json.loads(extracted.attributes) if extracted.attributes else {}

        # Generate slug
        name = attributes.get("entity_name", "unknown")
        slug = self.slug_generator.generate(name)

        # Build Entity data (matching actual Entity schema)
        external_ids_data = json.loads(extracted.external_ids) if extracted.external_ids else {}

        return {
            "slug": slug,
            "entity_class": extracted.entity_class,
            "entity_name": name,
            "summary": attributes.get("summary"),
            "canonical_activities": attributes.get("canonical_activities", []),
            "canonical_roles": attributes.get("canonical_roles", []),
            "canonical_place_types": attributes.get("canonical_place_types", []),
            "canonical_access": attributes.get("canonical_access", []),
            "latitude": attributes.get("latitude"),
            "longitude": attributes.get("longitude"),
            "street_address": attributes.get("street_address"),
            "city": attributes.get("city"),
            "postcode": attributes.get("postcode"),
            "country": attributes.get("country"),
            "phone": attributes.get("phone"),
            "email": attributes.get("email"),
            "website_url": attributes.get("website"),
            "modules": Json(attributes.get("modules", {})),
            "discovered_attributes": Json({}),
            "opening_hours": Json({}),
            "source_info": Json({}),
            "field_confidence": Json({}),
            "external_ids": Json(external_ids_data),
        }
