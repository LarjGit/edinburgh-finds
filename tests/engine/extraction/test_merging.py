"""
Tests for engine/extraction/merging.py — missingness predicate and FieldMerger filter.
"""

import pytest
from engine.extraction.merging import _is_missing, FieldValue, FieldMerger, TrustHierarchy, EntityMerger


# ---------------------------------------------------------------------------
# _is_missing unit tests
# ---------------------------------------------------------------------------

class TestIsMissing:
    """_is_missing must treat None, empty/whitespace strings, and known
    placeholders as missing.  Everything else is a real value."""

    # --- should be treated as missing ---
    @pytest.mark.parametrize("value", [
        None,
        "",
        "   ",
        "\t",
        "\n",
        " \t\n ",
        "N/A",
        "n/a",
        "NA",
        "-",
        "\u2013",          # en-dash –
        "\u2014",          # em-dash —
    ])
    def test_missing_values(self, value):
        assert _is_missing(value) is True

    # --- should NOT be treated as missing ---
    @pytest.mark.parametrize("value", [
        "hello",
        "0",
        " real value ",      # has non-whitespace content
        "N/A extra",         # placeholder substring, not exact match
        "-dash",             # starts with dash but is a real value
        0,                   # integer zero
        False,               # boolean False
        [],                  # empty list — not a string sentinel
        {},                  # empty dict — not a string sentinel
    ])
    def test_real_values(self, value):
        assert _is_missing(value) is False


# ---------------------------------------------------------------------------
# FieldMerger integration — empty string no longer blocks a real value
# ---------------------------------------------------------------------------

class TestFieldMergerMissnessFilter:
    """When one source returns "" and another returns a real value,
    the real value must win regardless of source trust order."""

    @pytest.fixture
    def merger(self, tmp_path):
        """FieldMerger backed by a minimal extraction.yaml with two sources."""
        cfg = tmp_path / "extraction.yaml"
        cfg.write_text(
            "trust_levels:\n"
            "  high_trust: 80\n"
            "  low_trust:  40\n"
            "  unknown_source: 10\n"
        )
        th = TrustHierarchy(config_path=str(cfg))
        return FieldMerger(trust_hierarchy=th)

    def test_empty_string_from_high_trust_does_not_block_real_value(self, merger):
        """high_trust returns ""; low_trust returns real text.
        Result must be the real text from low_trust."""
        values = [
            FieldValue(value="", source="high_trust", confidence=0.9),
            FieldValue(value="A great summary", source="low_trust", confidence=0.8),
        ]
        result = merger.merge_field("summary", values)
        assert result.value == "A great summary"
        assert result.source == "low_trust"

    def test_placeholder_from_high_trust_does_not_block_real_value(self, merger):
        """high_trust returns "N/A"; low_trust returns real text."""
        values = [
            FieldValue(value="N/A", source="high_trust", confidence=0.9),
            FieldValue(value="Useful description", source="low_trust", confidence=0.8),
        ]
        result = merger.merge_field("description", values)
        assert result.value == "Useful description"
        assert result.source == "low_trust"

    def test_both_missing_yields_none(self, merger):
        """Both sources are missing — result value is None."""
        values = [
            FieldValue(value="", source="high_trust", confidence=0.9),
            FieldValue(value="N/A", source="low_trust", confidence=0.8),
        ]
        result = merger.merge_field("summary", values)
        assert result.value is None

    def test_real_value_from_high_trust_still_wins(self, merger):
        """Normal case: both have real values, higher trust wins as before."""
        values = [
            FieldValue(value="High trust text", source="high_trust", confidence=0.9),
            FieldValue(value="Low trust text", source="low_trust", confidence=0.8),
        ]
        result = merger.merge_field("summary", values)
        assert result.value == "High trust text"
        assert result.source == "high_trust"


# ---------------------------------------------------------------------------
# DM-003: Field-group merge strategies
# ---------------------------------------------------------------------------


class TestEntityTypeDeterminism:
    """entity_type winner must be identical regardless of input ordering.
    Acceptance criterion 1: missingness filter → trust → connector_id asc."""

    @pytest.fixture
    def merger(self, tmp_path):
        cfg = tmp_path / "extraction.yaml"
        cfg.write_text(
            "trust_levels:\n"
            "  source_a: 60\n"
            "  source_b: 60\n"
            "  unknown_source: 10\n"
        )
        th = TrustHierarchy(config_path=str(cfg))
        return EntityMerger(trust_hierarchy=th)

    def test_entity_type_order_ab_equals_ba(self, merger):
        """Same-trust sources: connector_id ascending is the stable tie-break."""
        base = {"attributes": {"entity_name": "Test"}, "confidence": 0.9}
        a = {**base, "source": "source_a", "entity_type": "place"}
        b = {**base, "source": "source_b", "entity_type": "organization"}

        result_ab = merger.merge_entities([a, b])
        result_ba = merger.merge_entities([b, a])

        # Both orderings must produce the same winner
        assert result_ab["entity_type"] == result_ba["entity_type"]
        # "source_a" < "source_b" lexicographically → source_a's type wins
        assert result_ab["entity_type"] == "place"

    def test_entity_type_placeholder_filtered(self, merger):
        """entity_type 'N/A' is missing and does not block a real value."""
        base = {"attributes": {"entity_name": "Test"}, "confidence": 0.9}
        a = {**base, "source": "source_a", "entity_type": "N/A"}
        b = {**base, "source": "source_b", "entity_type": "place"}

        result = merger.merge_entities([a, b])
        assert result["entity_type"] == "place"


class TestProvenanceShapeConsistency:
    """source_info and field_confidence must always be dicts — never None —
    so single-source and multi-source outputs share the same structure.
    Acceptance criterion 2."""

    @pytest.fixture
    def merger(self, tmp_path):
        cfg = tmp_path / "extraction.yaml"
        cfg.write_text(
            "trust_levels:\n"
            "  source_a: 60\n"
            "  source_b: 40\n"
            "  unknown_source: 10\n"
        )
        th = TrustHierarchy(config_path=str(cfg))
        return EntityMerger(trust_hierarchy=th)

    def test_single_source_provenance_is_dict(self, merger):
        entity = {
            "source": "source_a",
            "entity_type": "place",
            "attributes": {"entity_name": "Test"},
            "confidence": 0.9,
        }
        result = merger.merge_entities([entity])
        assert isinstance(result["source_info"], dict)
        assert isinstance(result["field_confidence"], dict)

    def test_single_source_none_attributes_provenance_empty_dict(self, merger):
        """Explicit None attributes must not crash and must yield {} provenance."""
        entity = {
            "source": "source_a",
            "entity_type": "place",
            "attributes": None,
            "confidence": 0.9,
        }
        result = merger.merge_entities([entity])
        assert result["source_info"] == {}
        assert result["field_confidence"] == {}

    def test_multi_source_provenance_shape_matches_single(self, merger):
        """Both paths produce dict provenance even with empty attributes."""
        single = merger.merge_entities([{
            "source": "source_a", "entity_type": "place",
            "attributes": {}, "confidence": 0.9,
        }])
        multi = merger.merge_entities([
            {"source": "source_a", "entity_type": "place", "attributes": {}, "confidence": 0.9},
            {"source": "source_b", "entity_type": "place", "attributes": {}, "confidence": 0.8},
        ])
        assert type(single["source_info"]) is dict
        assert type(multi["source_info"]) is dict
        assert type(single["field_confidence"]) is dict
        assert type(multi["field_confidence"]) is dict


class TestGeoFieldStrategy:
    """Geo fields: presence via _is_missing filters, then trust decides.
    0 / 0.0 are valid coordinates and are NOT treated as missing."""

    @pytest.fixture
    def merger(self, tmp_path):
        cfg = tmp_path / "extraction.yaml"
        cfg.write_text(
            "trust_levels:\n"
            "  serper: 50\n"
            "  google_places: 70\n"
            "  unknown_source: 10\n"
        )
        th = TrustHierarchy(config_path=str(cfg))
        return FieldMerger(trust_hierarchy=th)

    def test_none_coord_loses_to_real_coord(self, merger):
        values = [
            FieldValue(value=None, source="serper", confidence=0.9),
            FieldValue(value=55.95, source="google_places", confidence=0.8),
        ]
        result = merger.merge_field("latitude", values)
        assert result.value == 55.95
        assert result.source == "google_places"

    def test_placeholder_coord_loses_to_real_coord(self, merger):
        values = [
            FieldValue(value="N/A", source="serper", confidence=0.9),
            FieldValue(value=-3.18, source="google_places", confidence=0.8),
        ]
        result = merger.merge_field("longitude", values)
        assert result.value == -3.18
        assert result.source == "google_places"

    def test_both_present_trust_decides(self, merger):
        values = [
            FieldValue(value=55.90, source="serper", confidence=0.9),
            FieldValue(value=55.95, source="google_places", confidence=0.8),
        ]
        result = merger.merge_field("latitude", values)
        assert result.value == 55.95
        assert result.source == "google_places"

    def test_zero_is_a_valid_coordinate(self, merger):
        """0.0 is equator / prime-meridian — not missing, participates normally."""
        values = [
            FieldValue(value=0.0, source="serper", confidence=0.9),
            FieldValue(value=55.95, source="google_places", confidence=0.8),
        ]
        result = merger.merge_field("latitude", values)
        # Both present; google_places trust 70 > serper 50
        assert result.value == 55.95
        assert result.source == "google_places"


class TestNarrativeFieldStrategy:
    """Narrative fields prefer richer (longer) text, then trust, then
    connector_id as tie-break."""

    @pytest.fixture
    def merger(self, tmp_path):
        cfg = tmp_path / "extraction.yaml"
        cfg.write_text(
            "trust_levels:\n"
            "  high_trust: 80\n"
            "  low_trust: 40\n"
            "  unknown_source: 10\n"
        )
        th = TrustHierarchy(config_path=str(cfg))
        return FieldMerger(trust_hierarchy=th)

    def test_longer_text_beats_higher_trust(self, merger):
        values = [
            FieldValue(value="Short", source="high_trust", confidence=0.9),
            FieldValue(value="A much richer and longer summary", source="low_trust", confidence=0.8),
        ]
        result = merger.merge_field("summary", values)
        assert result.value == "A much richer and longer summary"
        assert result.source == "low_trust"

    def test_same_length_trust_decides(self, merger):
        values = [
            FieldValue(value="AAAA", source="high_trust", confidence=0.9),
            FieldValue(value="BBBB", source="low_trust", confidence=0.8),
        ]
        result = merger.merge_field("description", values)
        assert result.value == "AAAA"
        assert result.source == "high_trust"

    def test_missing_narrative_filtered(self, merger):
        """Empty string from high_trust is filtered; real content wins."""
        values = [
            FieldValue(value="", source="high_trust", confidence=0.9),
            FieldValue(value="Real content here", source="low_trust", confidence=0.8),
        ]
        result = merger.merge_field("summary", values)
        assert result.value == "Real content here"
        assert result.source == "low_trust"


class TestCanonicalArrayMerge:
    """Canonical arrays: union + normalise (strip + lower) + dedup + sort.
    All sources contribute — no single winner.
    Acceptance criterion 3: strict deterministic ordering throughout."""

    @pytest.fixture
    def merger(self, tmp_path):
        cfg = tmp_path / "extraction.yaml"
        cfg.write_text(
            "trust_levels:\n"
            "  source_a: 60\n"
            "  source_b: 40\n"
            "  unknown_source: 10\n"
        )
        th = TrustHierarchy(config_path=str(cfg))
        return FieldMerger(trust_hierarchy=th)

    def test_union_dedup_sort(self, merger):
        values = [
            FieldValue(value=["tennis", "padel"], source="source_a", confidence=0.9),
            FieldValue(value=["padel", "squash"], source="source_b", confidence=0.8),
        ]
        result = merger.merge_field("canonical_activities", values)
        assert result.value == ["padel", "squash", "tennis"]
        assert result.source == "merged"
        assert result.confidence == 1.0

    def test_input_order_independent(self, merger):
        """Swapping source order yields identical result (strict equality)."""
        ab = [
            FieldValue(value=["tennis", "padel"], source="source_a", confidence=0.9),
            FieldValue(value=["padel", "squash"], source="source_b", confidence=0.8),
        ]
        ba = [
            FieldValue(value=["padel", "squash"], source="source_b", confidence=0.8),
            FieldValue(value=["tennis", "padel"], source="source_a", confidence=0.9),
        ]
        assert merger.merge_field("canonical_activities", ab).value == \
               merger.merge_field("canonical_activities", ba).value

    def test_normalisation_collapses_case_and_whitespace(self, merger):
        """'Padel', 'padel ', 'PADEL' → single 'padel'."""
        values = [
            FieldValue(value=["Padel", "Tennis"], source="source_a", confidence=0.9),
            FieldValue(value=["padel ", "PADEL", "squash"], source="source_b", confidence=0.8),
        ]
        result = merger.merge_field("canonical_activities", values)
        assert result.value == ["padel", "squash", "tennis"]

    def test_single_source_array_normalised_and_sorted(self, merger):
        values = [
            FieldValue(value=["Tennis", " padel "], source="source_a", confidence=0.9),
        ]
        result = merger.merge_field("canonical_activities", values)
        assert result.value == ["padel", "tennis"]

    def test_none_source_skipped(self, merger):
        """None array value doesn't block other source's values."""
        values = [
            FieldValue(value=None, source="source_a", confidence=0.9),
            FieldValue(value=["tennis"], source="source_b", confidence=0.8),
        ]
        result = merger.merge_field("canonical_activities", values)
        assert result.value == ["tennis"]

    def test_all_none_yields_empty_list(self, merger):
        values = [
            FieldValue(value=None, source="source_a", confidence=0.9),
            FieldValue(value=None, source="source_b", confidence=0.8),
        ]
        result = merger.merge_field("canonical_activities", values)
        assert result.value == []

    def test_placeholder_items_within_array_filtered(self, merger):
        """Individual items like 'N/A' or '' within a list are dropped."""
        values = [
            FieldValue(value=["tennis", "", "N/A", "padel"], source="source_a", confidence=0.9),
        ]
        result = merger.merge_field("canonical_activities", values)
        assert result.value == ["padel", "tennis"]

    def test_all_canonical_field_names_route_correctly(self, merger):
        """All four canonical array field names use the array strategy."""
        for field_name in ("canonical_activities", "canonical_roles",
                           "canonical_place_types", "canonical_access"):
            values = [
                FieldValue(value=["beta", "alpha"], source="source_a", confidence=0.9),
            ]
            result = merger.merge_field(field_name, values)
            assert result.value == ["alpha", "beta"], f"Failed for {field_name}"
            assert result.source == "merged"


# ---------------------------------------------------------------------------
# DM-005: Modules deep recursive merge (architecture.md 9.4)
# ---------------------------------------------------------------------------


class TestModulesDeepMerge:
    """modules field: deep recursive merge per docs/target-architecture.md 9.4.

    - Object vs object → recursive merge
    - Scalar arrays → concatenate, deduplicate, sort (strings trimmed only)
    - Object arrays → wholesale from winning source
    - Type mismatch → higher trust wins wholesale
    - Per-leaf: trust → confidence → source (asc)
    - Empty containers ({}, []) yield to populated counterpart naturally
    """

    @pytest.fixture
    def merger(self, tmp_path):
        cfg = tmp_path / "extraction.yaml"
        cfg.write_text(
            "trust_levels:\n"
            "  high_trust: 80\n"
            "  low_trust:  40\n"
            "  unknown_source: 10\n"
        )
        th = TrustHierarchy(config_path=str(cfg))
        return FieldMerger(trust_hierarchy=th)

    # --- object vs object: recursive merge ---

    def test_recursive_merge_nested_dicts(self, merger):
        """Disjoint nested keys are unioned; shared leaf keys resolve by trust."""
        high = {
            "sports_facility": {
                "pitch_count": 4,
                "surface": "artificial",
            }
        }
        low = {
            "sports_facility": {
                "pitch_count": 2,          # conflict → high_trust wins
                "floodlights": True,       # unique to low → included
            },
            "contact": {"phone": "555-1234"},  # unique module → included
        }
        values = [
            FieldValue(value=high, source="high_trust", confidence=0.9),
            FieldValue(value=low,  source="low_trust",  confidence=0.8),
        ]
        result = merger.merge_field("modules", values)

        assert result.value["sports_facility"]["pitch_count"] == 4
        assert result.value["sports_facility"]["surface"] == "artificial"
        assert result.value["sports_facility"]["floodlights"] is True
        assert result.value["contact"]["phone"] == "555-1234"
        assert result.source == "merged"

    # --- scalar arrays: concat + dedup + sort ---

    def test_scalar_array_concat_dedup_sort(self, merger):
        """Scalar string arrays across sources: concat, dedup, sort."""
        high = {"tags": ["indoor", "competitive"]}
        low  = {"tags": ["competitive", "beginner"]}
        values = [
            FieldValue(value=high, source="high_trust", confidence=0.9),
            FieldValue(value=low,  source="low_trust",  confidence=0.8),
        ]
        result = merger.merge_field("modules", values)
        assert result.value["tags"] == ["beginner", "competitive", "indoor"]

    def test_scalar_array_strings_trimmed_not_lowered(self, merger):
        """Strings are trimmed but NOT lowercased (modules are case-sensitive).
        'competitive' and 'Competitive' are distinct after trim."""
        high = {"tags": [" indoor ", "competitive"]}
        low  = {"tags": ["indoor", " Competitive "]}
        values = [
            FieldValue(value=high, source="high_trust", confidence=0.9),
            FieldValue(value=low,  source="low_trust",  confidence=0.8),
        ]
        result = merger.merge_field("modules", values)
        # "indoor" deduped to one; "competitive" != "Competitive" → both kept
        assert len(result.value["tags"]) == 3
        assert "indoor" in result.value["tags"]
        assert "competitive" in result.value["tags"]
        assert "Competitive" in result.value["tags"]

    # --- object arrays: wholesale from winning source ---

    def test_object_array_wholesale_from_winner(self, merger):
        """Arrays containing dicts are taken wholesale from highest-trust source."""
        high = {"schedules": [{"day": "Mon", "time": "09:00"}]}
        low  = {"schedules": [{"day": "Tue", "time": "10:00"}, {"day": "Wed", "time": "11:00"}]}
        values = [
            FieldValue(value=high, source="high_trust", confidence=0.9),
            FieldValue(value=low,  source="low_trust",  confidence=0.8),
        ]
        result = merger.merge_field("modules", values)
        assert result.value["schedules"] == [{"day": "Mon", "time": "09:00"}]

    # --- type mismatch: higher trust wins wholesale ---

    def test_type_mismatch_higher_trust_wins(self, merger):
        """Same key, incompatible types (str vs dict) → higher-trust value taken."""
        high = {"detail": "a plain string"}
        low  = {"detail": {"nested_key": "value"}}
        values = [
            FieldValue(value=high, source="high_trust", confidence=0.9),
            FieldValue(value=low,  source="low_trust",  confidence=0.8),
        ]
        result = merger.merge_field("modules", values)
        assert result.value["detail"] == "a plain string"

    # --- empty containers yield to populated ---

    def test_empty_dict_yields_to_populated(self, merger):
        """Source with {} modules doesn't block populated source's keys."""
        values = [
            FieldValue(value={},                            source="high_trust", confidence=0.9),
            FieldValue(value={"sports": {"courts": 3}},     source="low_trust",  confidence=0.8),
        ]
        result = merger.merge_field("modules", values)
        assert result.value == {"sports": {"courts": 3}}

    def test_empty_list_yields_to_populated_list(self, merger):
        """[] in one source doesn't block populated list in other (concat path)."""
        high = {"tags": []}
        low  = {"tags": ["indoor", "outdoor"]}
        values = [
            FieldValue(value=high, source="high_trust", confidence=0.9),
            FieldValue(value=low,  source="low_trust",  confidence=0.8),
        ]
        result = merger.merge_field("modules", values)
        assert result.value["tags"] == ["indoor", "outdoor"]

    # --- mixed-type scalar array: fall back to trust winner ---

    def test_mixed_type_array_falls_back_to_trust(self, merger):
        """Scalar array with mixed types (str + int) can't be sorted →
        trust winner takes the array wholesale."""
        high = {"ids": [1, "abc"]}
        low  = {"ids": [2, "def"]}
        values = [
            FieldValue(value=high, source="high_trust", confidence=0.9),
            FieldValue(value=low,  source="low_trust",  confidence=0.8),
        ]
        result = merger.merge_field("modules", values)
        assert result.value["ids"] == [1, "abc"]

    # --- input order independence ---

    def test_input_order_independent(self, merger):
        """Swapping source order produces identical merged modules."""
        a = {"sports": {"courts": 4}, "tags": ["indoor"]}
        b = {"sports": {"lights": True}, "tags": ["outdoor"]}
        ab = [
            FieldValue(value=a, source="high_trust", confidence=0.9),
            FieldValue(value=b, source="low_trust",  confidence=0.8),
        ]
        ba = [
            FieldValue(value=b, source="low_trust",  confidence=0.8),
            FieldValue(value=a, source="high_trust", confidence=0.9),
        ]
        assert merger.merge_field("modules", ab).value == \
               merger.merge_field("modules", ba).value


class TestModulesDeepMergeSameTrust:
    """Per-leaf confidence and source tie-break when trust levels are equal."""

    @pytest.fixture
    def merger(self, tmp_path):
        cfg = tmp_path / "extraction.yaml"
        cfg.write_text(
            "trust_levels:\n"
            "  source_a: 60\n"
            "  source_b: 60\n"
            "  unknown_source: 10\n"
        )
        th = TrustHierarchy(config_path=str(cfg))
        return FieldMerger(trust_hierarchy=th)

    def test_same_trust_higher_confidence_wins_leaf(self, merger):
        """Equal trust → confidence decides the leaf value."""
        a = {"detail": {"name": "Version A"}}
        b = {"detail": {"name": "Version B"}}
        values = [
            FieldValue(value=a, source="source_a", confidence=0.9),
            FieldValue(value=b, source="source_b", confidence=0.5),
        ]
        result = merger.merge_field("modules", values)
        assert result.value["detail"]["name"] == "Version A"

    def test_same_trust_same_confidence_source_id_tiebreak(self, merger):
        """Equal trust, equal confidence → lexicographic source_id wins."""
        a = {"detail": {"name": "A value"}}
        b = {"detail": {"name": "B value"}}
        values = [
            FieldValue(value=a, source="source_a", confidence=0.8),
            FieldValue(value=b, source="source_b", confidence=0.8),
        ]
        result = merger.merge_field("modules", values)
        # source_a < source_b lexicographically → source_a wins
        assert result.value["detail"]["name"] == "A value"
