"""Test EntityFinalizer (TDD)."""

import pytest
import json
from unittest.mock import Mock, patch
from prisma import Prisma
from engine.orchestration.entity_finalizer import EntityFinalizer


class TestFinalizeSingleCanonicalKeys:
    """Unit tests: _finalize_single must read canonical schema keys only."""

    def _make_extracted(self, attributes: dict, entity_class: str = "place", external_ids: dict = None, source: str = "unknown_source", discovered_attributes: dict = None):
        """Helper: build a mock ExtractedEntity with the given attributes JSON."""
        mock = Mock()
        mock.attributes = json.dumps(attributes)
        mock.external_ids = json.dumps(external_ids or {})
        mock.discovered_attributes = json.dumps(discovered_attributes or {})
        mock.entity_class = entity_class
        mock.source = source
        mock.id = str(id(mock))
        return mock

    def test_latitude_longitude_read_from_canonical_keys(self):
        """
        Extractors output latitude / longitude.  Finalizer must read exactly
        those keys — no legacy aliases (location_lat, location_lng).
        """
        finalizer = EntityFinalizer(db=None)
        extracted = self._make_extracted({
            "entity_name": "Coord Venue",
            "latitude": 55.9533,
            "longitude": -3.1883,
        })

        result = finalizer._finalize_single(extracted)

        assert result["latitude"] == 55.9533
        assert result["longitude"] == -3.1883

    def test_address_fields_read_from_canonical_keys(self):
        """
        Extractors output street_address / city / postcode / country.
        Finalizer must read exactly those keys — no legacy aliases
        (address_full, address_street, address_city, address_postal_code, address_country).
        """
        finalizer = EntityFinalizer(db=None)
        extracted = self._make_extracted({
            "entity_name": "Address Venue",
            "street_address": "42 Test Road",
            "city": "Edinburgh",
            "postcode": "EH1 2AB",
            "country": "Scotland",
        })

        result = finalizer._finalize_single(extracted)

        assert result["street_address"] == "42 Test Road"
        assert result["city"] == "Edinburgh"
        assert result["postcode"] == "EH1 2AB"
        assert result["country"] == "Scotland"

    def test_contact_fields_read_from_canonical_keys(self):
        """
        Extractors output phone / email / website.
        Finalizer must map phone → phone, email → email, website → website_url.
        No legacy aliases (contact_phone, contact_email, contact_website).
        """
        finalizer = EntityFinalizer(db=None)
        extracted = self._make_extracted({
            "entity_name": "Contact Venue",
            "phone": "+441315551234",
            "email": "test@example.com",
            "website": "https://example.com",
        })

        result = finalizer._finalize_single(extracted)

        assert result["phone"] == "+441315551234"
        assert result["email"] == "test@example.com"
        assert result["website_url"] == "https://example.com"

    def test_legacy_keys_are_ignored(self):
        """
        Legacy attribute keys must NOT propagate to Entity output.

        Attributes containing only legacy keys (location_lat, location_lng,
        address_full, address_city, contact_phone, contact_email,
        contact_website) must produce None for the corresponding Entity fields.
        Only the canonical schema keys are read.
        """
        finalizer = EntityFinalizer(db=None)
        extracted = self._make_extracted({
            "entity_name": "Legacy Venue",
            # All legacy — none should map
            "location_lat": 55.9533,
            "location_lng": -3.1883,
            "address_full": "42 Legacy Road",
            "address_city": "Edinburgh",
            "address_postal_code": "EH1 2AB",
            "address_country": "Scotland",
            "contact_phone": "+441315551234",
            "contact_email": "legacy@example.com",
            "contact_website": "https://legacy.example.com",
        })

        result = finalizer._finalize_single(extracted)

        # All location / contact fields must be None — legacy keys ignored
        assert result["latitude"] is None
        assert result["longitude"] is None
        assert result["street_address"] is None
        assert result["city"] is None
        assert result["postcode"] is None
        assert result["country"] is None
        assert result["phone"] is None
        assert result["email"] is None
        assert result["website_url"] is None

    def test_legacy_name_key_ignored(self):
        """
        The legacy 'name' key must not be used as a fallback.  If entity_name
        is missing the slug must derive from 'unknown', not from 'name'.
        """
        finalizer = EntityFinalizer(db=None)
        extracted = self._make_extracted({
            # Deliberately no entity_name — only the old 'name' key
            "name": "Should Not Appear",
        })

        result = finalizer._finalize_single(extracted)

        assert result["entity_name"] == "unknown"
        assert result["slug"] == "unknown"

    @pytest.mark.asyncio
    async def test_multi_source_merge_fills_nulls_from_richer_source(self):
        """
        When multiple sources produce the same slug, _finalize_group must
        merge fields: first non-null value wins across the group.

        Serper (source 0) has the name + city but no coordinates.
        Google Places (source 1) has coordinates + street but no city.
        Merged result should have ALL fields populated.
        """
        finalizer = EntityFinalizer(db=None)

        serper_entity = self._make_extracted({
            "entity_name": "Merge Test Venue",
            "city": "Edinburgh",
            "canonical_activities": ["padel"],
            "modules": {"sports_facility": {"padel_courts": {"total": 2}}},
        }, entity_class="place")

        gp_entity = self._make_extracted({
            "entity_name": "Merge Test Venue",
            "latitude": 55.9533,
            "longitude": -3.1883,
            "street_address": "42 Test Road",
            "phone": "+441315551234",
        }, entity_class="place")

        # Serper first (as in real pipeline order), GP second
        result = await finalizer._finalize_group([serper_entity, gp_entity])

        # Fields from Serper (first non-null)
        assert result["city"] == "Edinburgh"
        assert result["canonical_activities"] == ["padel"]

        # Fields from GP (Serper had None, GP fills them)
        assert result["latitude"] == 55.9533
        assert result["longitude"] == -3.1883
        assert result["street_address"] == "42 Test Road"
        assert result["phone"] == "+441315551234"


class TestFinalizeGroupTrustOrderIndependence:
    """_finalize_group must delegate to EntityMerger so that trust — not
    insertion order — decides the winner.  Running the same group in both
    orderings must produce identical payloads for every scalar field."""

    def _make(self, attributes: dict, source: str, entity_class: str = "place",
              external_ids: dict = None, discovered_attributes: dict = None):
        mock = Mock()
        mock.attributes = json.dumps(attributes)
        mock.external_ids = json.dumps(external_ids or {})
        mock.discovered_attributes = json.dumps(discovered_attributes or {})
        mock.entity_class = entity_class
        mock.source = source
        mock.id = str(id(mock))
        return mock

    @pytest.mark.asyncio
    async def test_trust_wins_regardless_of_list_order(self):
        """google_places (trust 70) summary must beat serper (trust 50)
        whether google_places appears first or second in the group.
        All scalar fields must be bit-identical across the two orderings."""
        finalizer = EntityFinalizer(db=None)

        gp = self._make(
            source="google_places",
            attributes={
                "entity_name": "Order Test Venue",
                "summary": "GP summary — high trust",
                "latitude": 55.95,
                "longitude": -3.19,
            },
            external_ids={"google_place_id": "ChIJ_gp_001"},
            discovered_attributes={"note": "from GP"},
        )

        serper = self._make(
            source="serper",
            attributes={
                "entity_name": "Order Test Venue",
                "summary": "Serper summary — low trust",
                "city": "Edinburgh",
            },
            external_ids={"serper_id": "serp_001"},
            discovered_attributes={"note": "from serper"},
        )

        result_gp_first = await finalizer._finalize_group([gp, serper])
        result_serper_first = await finalizer._finalize_group([serper, gp])

        # --- narrative strategy: longer text wins summary in both orderings ---
        # "Serper summary — low trust" (26 chars) > "GP summary — high trust" (24 chars)
        assert result_gp_first["summary"] == "Serper summary — low trust"
        assert result_serper_first["summary"] == "Serper summary — low trust"

        # --- every scalar / array field is order-independent ---
        scalar_keys = [
            "slug", "entity_class", "entity_name", "summary",
            "latitude", "longitude", "street_address", "city",
            "postcode", "country", "phone", "email", "website_url",
            "canonical_activities", "canonical_roles",
            "canonical_place_types", "canonical_access",
        ]
        for key in scalar_keys:
            assert result_gp_first[key] == result_serper_first[key], (
                f"field {key!r} differs by input order: "
                f"{result_gp_first[key]!r} vs {result_serper_first[key]!r}"
            )

        # --- non-overlapping fields from both sources survived the merge ---
        assert result_gp_first["latitude"] == 55.95
        assert result_gp_first["longitude"] == -3.19
        assert result_gp_first["city"] == "Edinburgh"


class TestFinalizeGroupPreMergerSort:
    """_finalize_group must sort the group by (trust desc, source asc, id asc)
    before EntityMerger sees it.  This is a contract-boundary determinism
    guarantee — independent of merger internals."""

    def _make(self, source: str, entity_id: str, marker: str):
        """Mock with a unique marker in external_ids for order tracing."""
        mock = Mock()
        mock.attributes = json.dumps({"entity_name": "Sort Test"})
        mock.external_ids = json.dumps({"marker": marker})
        mock.discovered_attributes = json.dumps({})
        mock.entity_class = "place"
        mock.source = source
        mock.id = entity_id
        return mock

    @pytest.mark.asyncio
    async def test_group_sorted_trust_desc_source_asc_id_asc(self):
        """Three entities (two serper, one google_places) arrive scrambled.
        Finaliser must emit them to merger in:
          1. google_places  (trust 70)
          2. serper id-1    (trust 50, id tie-break wins)
          3. serper id-2    (trust 50)
        Markers in external_ids trace each entity through merger_inputs.
        """
        finalizer = EntityFinalizer(db=None)

        # Deliberately scrambled input order
        group = [
            self._make("serper",        "id-2", "s2"),
            self._make("google_places", "id-1", "gp"),
            self._make("serper",        "id-1", "s1"),
        ]

        with patch(
            "engine.orchestration.entity_finalizer.EntityMerger"
        ) as MockMergerCls:
            mock_merger = Mock()
            mock_merger.merge_entities.return_value = {
                "entity_type": "place",
                "entity_name": "Sort Test",
                "external_ids": {},
                "source_info": {},
                "field_confidence": {},
                "discovered_attributes": {},
            }
            MockMergerCls.return_value = mock_merger

            await finalizer._finalize_group(group)

            merger_inputs = mock_merger.merge_entities.call_args[0][0]
            markers = [inp["external_ids"]["marker"] for inp in merger_inputs]

        assert markers == ["gp", "s1", "s2"], (
            f"Expected trust-desc / source-asc / id-asc order; got {markers}"
        )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_finalize_single_entity():
    """Test finalization of single ExtractedEntity (no merging)."""
    db = Prisma()
    await db.connect()

    # Setup: Create OrchestrationRun
    orchestration_run = await db.orchestrationrun.create(
        data={
            "query": "test query",
            "status": "completed",
            "ingestion_mode": "DISCOVER_MANY"
        }
    )

    # Setup: Create RawIngestion
    raw_ingestion = await db.rawingestion.create(
        data={
            "orchestration_run_id": orchestration_run.id,
            "source": "test_source",
            "source_url": "https://test.com/123",
            "file_path": "test/path.json",
            "status": "success",
            "hash": "test-hash-123"
        }
    )

    # Setup: Create ExtractedEntity
    attributes = {
        "entity_name": "Test Venue",
        "latitude": 55.9533,
        "longitude": -3.1883,
        "canonical_activities": ["padel"],
        "canonical_roles": ["provides_facility"]
    }

    extracted = await db.extractedentity.create(
        data={
            "raw_ingestion_id": raw_ingestion.id,
            "source": "test_source",
            "entity_class": "place",
            "attributes": json.dumps(attributes),
            "external_ids": json.dumps({"test": "test-123"})
        }
    )

    # Act: Finalize entities
    finalizer = EntityFinalizer(db)
    stats = await finalizer.finalize_entities(orchestration_run.id)

    # Assert: Stats
    assert stats["entities_created"] == 1
    assert stats["entities_updated"] == 0

    # Assert: Entity created
    entities = await db.entity.find_many(
        where={"entity_name": "Test Venue"}
    )
    assert len(entities) == 1

    entity = entities[0]
    assert entity.slug == "test-venue"
    assert entity.entity_class == "place"
    assert entity.entity_name == "Test Venue"
    assert entity.latitude == 55.9533
    assert "padel" in entity.canonical_activities

    # Cleanup
    await db.entity.delete(where={"id": entity.id})
    await db.extractedentity.delete(where={"id": extracted.id})
    await db.rawingestion.delete(where={"id": raw_ingestion.id})
    await db.orchestrationrun.delete(where={"id": orchestration_run.id})
    await db.disconnect()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_finalize_idempotent():
    """Test that re-finalizing updates existing Entity (idempotent)."""
    db = Prisma()
    await db.connect()

    # Setup: Create test data
    orchestration_run = await db.orchestrationrun.create(
        data={
            "query": "test query",
            "status": "completed",
            "ingestion_mode": "DISCOVER_MANY"
        }
    )

    raw_ingestion = await db.rawingestion.create(
        data={
            "orchestration_run_id": orchestration_run.id,
            "source": "test_source",
            "source_url": "https://test.com/456",
            "file_path": "test/path2.json",
            "status": "success",
            "hash": "test-hash-456"
        }
    )

    attributes = {
        "entity_name": "Idempotent Venue",
        "latitude": 55.9533,
        "longitude": -3.1883
    }

    extracted = await db.extractedentity.create(
        data={
            "raw_ingestion_id": raw_ingestion.id,
            "source": "test_source",
            "entity_class": "place",
            "attributes": json.dumps(attributes),
            "external_ids": json.dumps({})
        }
    )

    # Act: First finalization
    finalizer = EntityFinalizer(db)
    stats1 = await finalizer.finalize_entities(orchestration_run.id)

    entities_after_first = await db.entity.find_many(
        where={"entity_name": "Idempotent Venue"}
    )
    assert len(entities_after_first) == 1
    first_entity_id = entities_after_first[0].id

    # Act: Second finalization (idempotent)
    stats2 = await finalizer.finalize_entities(orchestration_run.id)

    # Assert: Updated, not duplicated
    assert stats2["entities_created"] == 0
    assert stats2["entities_updated"] == 1

    entities_after_second = await db.entity.find_many(
        where={"entity_name": "Idempotent Venue"}
    )
    assert len(entities_after_second) == 1
    assert entities_after_second[0].id == first_entity_id

    # Cleanup
    await db.entity.delete(where={"id": first_entity_id})
    await db.extractedentity.delete(where={"id": extracted.id})
    await db.rawingestion.delete(where={"id": raw_ingestion.id})
    await db.orchestrationrun.delete(where={"id": orchestration_run.id})
    await db.disconnect()
