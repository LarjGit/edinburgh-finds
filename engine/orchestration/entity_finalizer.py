"""Entity Finalization - Bridge from ExtractedEntity to Entity table."""

import json
import logging
from typing import List, Dict, Optional, Any
from prisma import Prisma, Json
from prisma.models import ExtractedEntity
from engine.extraction.deduplication import SlugGenerator
from engine.extraction.merging import EntityMerger, TrustHierarchy

logger = logging.getLogger(__name__)


class EntityFinalizer:
    """Finalize entities from extraction to published Entity records."""

    def __init__(self, db: Prisma):
        self.db = db
        self.slug_generator = SlugGenerator()
        self.trust_hierarchy = TrustHierarchy()

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

        Single-entity groups take the fast path via _finalize_single.
        Multi-entity groups are merged by EntityMerger (trust-aware,
        missingness-filtered) and mapped to the upsert payload via the
        shared _build_upsert_payload helper.
        """
        if len(entity_group) == 1:
            return self._finalize_single(entity_group[0])

        # Deterministic contract-boundary sort — trust desc, connector_id asc,
        # DB primary-key asc.  Pins input order so the finaliser boundary is
        # stable regardless of DB query-plan or insertion order.
        entity_group = sorted(entity_group, key=lambda e: (
            -self.trust_hierarchy.get_trust_level(e.source),
            e.source,
            e.id,
        ))

        # Build input dicts — every merge-relevant blob from ExtractedEntity
        merger_inputs = []
        for entity in entity_group:
            merger_inputs.append({
                "source": entity.source,
                "entity_type": entity.entity_class,
                "attributes": json.loads(entity.attributes) if entity.attributes else {},
                "discovered_attributes": json.loads(entity.discovered_attributes) if entity.discovered_attributes else {},
                "external_ids": json.loads(entity.external_ids) if entity.external_ids else {},
            })

        merged = EntityMerger().merge_entities(merger_inputs)

        return self._build_upsert_payload(
            attributes=merged,
            entity_class=merged.get("entity_type") or entity_group[0].entity_class,
            external_ids=merged.get("external_ids", {}),
            source_info=merged.get("source_info", {}),
            field_confidence=merged.get("field_confidence", {}),
            discovered_attributes=merged.get("discovered_attributes", {}),
        )

    def _finalize_single(self, extracted: ExtractedEntity) -> Dict[str, Any]:
        """Convert single ExtractedEntity to Entity format via the shared
        upsert-payload helper.  Provenance fields default to empty — there is
        only one source, so no merge conflict to record."""
        attributes = json.loads(extracted.attributes) if extracted.attributes else {}
        external_ids = json.loads(extracted.external_ids) if extracted.external_ids else {}
        return self._build_upsert_payload(
            attributes=attributes,
            entity_class=extracted.entity_class,
            external_ids=external_ids,
        )

    def _build_upsert_payload(
        self,
        attributes: Dict[str, Any],
        entity_class: str,
        external_ids: Dict[str, Any],
        source_info: Optional[Dict[str, Any]] = None,
        field_confidence: Optional[Dict[str, Any]] = None,
        discovered_attributes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Map a flat attributes dict to the canonical Entity upsert payload.

        This is the single mapping surface for attribute-key → Entity-column
        normalization (e.g. website → website_url, slug generation).  Both
        _finalize_single and _finalize_group route through here so the mapping
        stays in sync.
        """
        name = attributes.get("entity_name", "unknown")
        slug = self.slug_generator.generate(name)

        return {
            "slug": slug,
            "entity_class": entity_class,
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
            "discovered_attributes": Json(discovered_attributes or {}),
            "opening_hours": Json({}),
            "source_info": Json(source_info or {}),
            "field_confidence": Json(field_confidence or {}),
            "external_ids": Json(external_ids),
        }
