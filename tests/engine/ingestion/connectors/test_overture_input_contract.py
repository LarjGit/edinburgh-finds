import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "overture" / "overture_places_contract_samples.json"
DOC_PATH = REPO_ROOT / "docs" / "progress" / "overture_input_contract.md"
REQUIRED_FIELDS = ("id", "version", "sources", "names", "categories", "geometry")


def _load_contract_samples() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _validate_overture_place_row(record: dict) -> None:
    if not isinstance(record, dict):
        raise ValueError("Overture place row must be a JSON object")

    if record.get("type") == "FeatureCollection" or "features" in record:
        raise ValueError(
            "Unsupported Overture contract: GeoJSON FeatureCollection wrapper is not accepted; "
            "expected row-style place record"
        )

    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"Overture place row missing required fields: {', '.join(missing)}")

    if not isinstance(record["sources"], list) or not record["sources"]:
        raise ValueError("Overture place row field 'sources' must be a non-empty list")

    if not isinstance(record["names"], dict) or not record["names"].get("primary"):
        raise ValueError("Overture place row field 'names.primary' is required")

    if not isinstance(record["categories"], dict) or "primary" not in record["categories"]:
        raise ValueError("Overture place row field 'categories.primary' is required")

    geometry = record["geometry"]
    if isinstance(geometry, dict):
        if geometry.get("type") != "Point":
            raise ValueError("Overture place row geometry must be a Point when represented as JSON")
        coords = geometry.get("coordinates")
        if not isinstance(coords, list) or len(coords) != 2:
            raise ValueError("Overture place row geometry Point must include two coordinates")
    elif not isinstance(geometry, (str, bytes)):
        raise ValueError(
            "Overture place row field 'geometry' must be GeoParquet WKB (binary/string) or JSON Point"
        )


def test_contract_fixture_accepts_official_row_style_samples():
    contract = _load_contract_samples()

    assert contract["accepted_shape"] == "row_place_records"
    assert contract["official_sources"]
    for sample in contract["valid_samples"]:
        _validate_overture_place_row(sample)


def test_contract_fixture_rejects_feature_collection_wrapper():
    contract = _load_contract_samples()
    invalid = next(
        item for item in contract["invalid_samples"] if item["label"] == "feature_collection_wrapper"
    )

    with pytest.raises(ValueError, match="FeatureCollection wrapper is not accepted"):
        _validate_overture_place_row(invalid["record"])


def test_contract_fixture_rejects_missing_required_field_with_explicit_message():
    contract = _load_contract_samples()
    invalid = next(item for item in contract["invalid_samples"] if item["label"] == "missing_required_fields")

    with pytest.raises(ValueError, match="missing required fields: sources"):
        _validate_overture_place_row(invalid["record"])


def test_contract_doc_includes_sources_and_access_date():
    contract = _load_contract_samples()
    doc_text = DOC_PATH.read_text(encoding="utf-8")

    assert "Accessed: 2026-02-15" in doc_text
    for link in contract["official_sources"]:
        assert link in doc_text
