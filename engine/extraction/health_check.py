"""
Extraction Health Check Metrics.

Provides helper functions to calculate extraction health metrics for
dashboard reporting. Metrics are computed from in-memory records to
support unit tests and database-backed callers.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from engine.extraction.schema_utils import get_extraction_fields


DEFAULT_LLM_SOURCES = {"serper", "osm"}
DEFAULT_INPUT_COST_PER_MILLION = 0.80
DEFAULT_OUTPUT_COST_PER_MILLION = 4.00


def now_utc() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


def _get_value(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


def _safe_json_load(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _normalize_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            if text.endswith("Z"):
                text = f"{text[:-1]}+00:00"
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def _extract_llm_usage(record: Any) -> Optional[Dict[str, int]]:
    direct_usage = _get_value(record, "llm_usage")
    if isinstance(direct_usage, dict):
        return direct_usage

    attributes = _safe_json_load(_get_value(record, "attributes"))
    if "llm_usage" in attributes and isinstance(attributes["llm_usage"], dict):
        return attributes["llm_usage"]
    if "_llm_usage" in attributes and isinstance(attributes["_llm_usage"], dict):
        return attributes["_llm_usage"]

    discovered = _safe_json_load(_get_value(record, "discovered_attributes"))
    if "llm_usage" in discovered and isinstance(discovered["llm_usage"], dict):
        return discovered["llm_usage"]
    if "_llm_usage" in discovered and isinstance(discovered["_llm_usage"], dict):
        return discovered["_llm_usage"]

    return None


def calculate_unprocessed_count(
    raw_records: List[Any],
    extracted_listings: List[Any],
    failed_extractions: List[Any],
) -> Dict[str, Any]:
    """Calculate counts of unprocessed raw ingestion records."""
    processed_ids = {
        _get_value(record, "raw_ingestion_id")
        for record in extracted_listings
        if _get_value(record, "raw_ingestion_id") is not None
    }
    processed_ids.update(
        _get_value(record, "raw_ingestion_id")
        for record in failed_extractions
        if _get_value(record, "raw_ingestion_id") is not None
    )

    unprocessed = []
    for record in raw_records:
        status = _get_value(record, "status")
        record_id = _get_value(record, "id")
        if status != "success":
            continue
        if record_id in processed_ids:
            continue
        unprocessed.append(record)

    by_source: Dict[str, int] = {}
    for record in unprocessed:
        source = _get_value(record, "source", "unknown")
        by_source[source] = by_source.get(source, 0) + 1

    return {
        "count": len(unprocessed),
        "by_source": by_source,
    }


def calculate_success_rate_by_source(
    raw_records: List[Any],
    extracted_listings: List[Any],
) -> Dict[str, Dict[str, Any]]:
    """Calculate extraction success rates by source."""
    totals: Dict[str, int] = {}
    for record in raw_records:
        if _get_value(record, "status") != "success":
            continue
        source = _get_value(record, "source", "unknown")
        totals[source] = totals.get(source, 0) + 1

    extracted_counts: Dict[str, int] = {}
    for listing in extracted_listings:
        source = _get_value(listing, "source", "unknown")
        extracted_counts[source] = extracted_counts.get(source, 0) + 1

    results: Dict[str, Dict[str, Any]] = {}
    for source, total in totals.items():
        extracted = extracted_counts.get(source, 0)
        success_rate = (extracted / total * 100.0) if total else 0.0
        results[source] = {
            "total": total,
            "extracted": extracted,
            "success_rate": success_rate,
        }

    for source, extracted in extracted_counts.items():
        if source not in results:
            results[source] = {
                "total": 0,
                "extracted": extracted,
                "success_rate": 0.0,
            }

    return results


def calculate_field_null_rates(
    extracted_listings: List[Any],
    field_names: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Calculate null rates for extraction fields."""
    if field_names is None:
        field_names = [field.name for field in get_extraction_fields()]

    total = len(extracted_listings)
    results: Dict[str, Dict[str, Any]] = {}

    for field_name in field_names:
        null_count = 0
        for record in extracted_listings:
            attributes = _safe_json_load(_get_value(record, "attributes"))
            value = attributes.get(field_name)
            if value is None:
                null_count += 1
        null_rate = (null_count / total * 100.0) if total else 0.0
        results[field_name] = {
            "null_count": null_count,
            "total": total,
            "null_rate": null_rate,
        }

    return results


def get_recent_failures(
    failed_extractions: List[Any],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Return recent failed extractions, sorted by last attempt time."""
    def failure_timestamp(record: Any) -> datetime:
        last_attempt = _normalize_timestamp(_get_value(record, "last_attempt_at"))
        if last_attempt is None:
            last_attempt = _normalize_timestamp(_get_value(record, "createdAt"))
        if last_attempt is None:
            last_attempt = _normalize_timestamp(_get_value(record, "created_at"))
        if last_attempt is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        return last_attempt

    ordered = sorted(
        failed_extractions,
        key=failure_timestamp,
        reverse=True,
    )

    result: List[Dict[str, Any]] = []
    for record in ordered[:limit]:
        result.append(
            {
                "id": _get_value(record, "id"),
                "source": _get_value(record, "source"),
                "error_message": _get_value(record, "error_message"),
                "last_attempt_at": _get_value(record, "last_attempt_at"),
            }
        )
    return result


def calculate_llm_usage(
    extracted_listings: List[Any],
    llm_sources: Optional[Iterable[str]] = None,
    input_cost_per_million: float = DEFAULT_INPUT_COST_PER_MILLION,
    output_cost_per_million: float = DEFAULT_OUTPUT_COST_PER_MILLION,
) -> Dict[str, Any]:
    """Calculate LLM usage metrics and estimated cost."""
    llm_sources_set = set(llm_sources) if llm_sources is not None else DEFAULT_LLM_SOURCES

    total_llm = 0
    by_model: Dict[str, int] = {}
    total_input_tokens = 0
    total_output_tokens = 0
    has_usage_data = False

    for record in extracted_listings:
        source = _get_value(record, "source", "unknown")
        model_used = _get_value(record, "model_used")

        is_llm = model_used is not None or source in llm_sources_set
        if not is_llm:
            continue

        total_llm += 1
        model_label = model_used or "unknown"
        by_model[model_label] = by_model.get(model_label, 0) + 1

        usage = _extract_llm_usage(record)
        if usage:
            input_tokens = int(usage.get("input_tokens", 0) or 0)
            output_tokens = int(usage.get("output_tokens", 0) or 0)
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            has_usage_data = True

    estimated_cost = (
        (total_input_tokens / 1_000_000) * input_cost_per_million
        + (total_output_tokens / 1_000_000) * output_cost_per_million
    )

    return {
        "total_llm_extractions": total_llm,
        "by_model": by_model,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "estimated_cost": estimated_cost,
        "has_usage_data": has_usage_data,
    }


def calculate_merge_conflict_count(merge_conflicts: Optional[List[Any]]) -> int:
    """Return merge conflict count."""
    if not merge_conflicts:
        return 0
    return len(merge_conflicts)


def calculate_health_metrics(
    raw_records: List[Any],
    extracted_listings: List[Any],
    failed_extractions: List[Any],
    merge_conflicts: Optional[List[Any]] = None,
    field_names: Optional[List[str]] = None,
    llm_sources: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Aggregate extraction health metrics into a single response."""
    return {
        "timestamp": now_utc().isoformat(),
        "unprocessed": calculate_unprocessed_count(
            raw_records, extracted_listings, failed_extractions
        ),
        "success_rate_by_source": calculate_success_rate_by_source(
            raw_records, extracted_listings
        ),
        "field_null_rates": calculate_field_null_rates(
            extracted_listings, field_names
        ),
        "recent_failures": get_recent_failures(failed_extractions),
        "llm_usage": calculate_llm_usage(
            extracted_listings, llm_sources=llm_sources
        ),
        "merge_conflicts": calculate_merge_conflict_count(merge_conflicts),
    }
