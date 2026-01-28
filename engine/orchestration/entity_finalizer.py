"""Entity Finalization - Bridge from ExtractedEntity to Entity table."""

import json
from typing import List, Dict, Optional, Any
from prisma import Prisma, Json
from prisma.models import ExtractedEntity
from engine.extraction.deduplication import SlugGenerator


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
        # 1. Load extracted entities for this run
        extracted_entities = await self.db.extractedentity.find_many(
            where={
                "raw_ingestion": {
                    "orchestration_run_id": orchestration_run_id
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
            name = attributes.get("name", "unknown")
            key = f"slug:{self.slug_generator.generate(name)}"

            if key not in groups:
                groups[key] = []
            groups[key].append(entity)

        return groups

    async def _finalize_group(
        self,
        entity_group: List[ExtractedEntity]
    ) -> Dict[str, Any]:
        """Finalize a group of ExtractedEntity records into Entity data."""
        if len(entity_group) == 1:
            # Single source - no merging needed
            return self._finalize_single(entity_group[0])

        # Multi-source merging (simplified - just use first for now)
        # TODO: Implement proper EntityMerger integration
        return self._finalize_single(entity_group[0])

    def _finalize_single(self, extracted: ExtractedEntity) -> Dict[str, Any]:
        """Convert single ExtractedEntity to Entity format."""
        attributes = json.loads(extracted.attributes) if extracted.attributes else {}

        # Generate slug
        name = attributes.get("name", "unknown")
        slug = self.slug_generator.generate(name)

        # Build Entity data (matching actual Entity schema)
        external_ids_data = json.loads(extracted.external_ids) if extracted.external_ids else {}

        # Handle field name variations (legacy vs new naming)
        latitude = attributes.get("location_lat") or attributes.get("latitude")
        longitude = attributes.get("location_lng") or attributes.get("longitude")
        street_address = (
            attributes.get("address_full") or
            attributes.get("address_street") or
            attributes.get("address")
        )

        return {
            "slug": slug,
            "entity_class": extracted.entity_class,
            "entity_name": name,
            "summary": attributes.get("summary"),
            "canonical_activities": attributes.get("canonical_activities", []),
            "canonical_roles": attributes.get("canonical_roles", []),
            "canonical_place_types": attributes.get("canonical_place_types", []),
            "canonical_access": attributes.get("canonical_access", []),
            "latitude": latitude,
            "longitude": longitude,
            "street_address": street_address,
            "city": attributes.get("address_city") or attributes.get("city"),
            "postcode": attributes.get("address_postal_code") or attributes.get("postcode"),
            "country": attributes.get("address_country") or attributes.get("country"),
            "phone": attributes.get("contact_phone") or attributes.get("phone"),
            "email": attributes.get("contact_email") or attributes.get("email"),
            "website_url": attributes.get("contact_website") or attributes.get("website"),
            "modules": Json(attributes.get("modules", {})),
            "discovered_attributes": Json({}),
            "opening_hours": Json({}),
            "source_info": Json({}),
            "field_confidence": Json({}),
            "external_ids": Json(external_ids_data),
        }
