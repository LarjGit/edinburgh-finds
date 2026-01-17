"""
Extraction quarantine and retry utilities.

Records failed extractions, retries them with max retry enforcement, and stores
successful ExtractedListing records.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable

from prisma import Prisma

from engine.extraction.extractors import (
    GooglePlacesExtractor,
    SportScotlandExtractor,
    EdinburghCouncilExtractor,
    OpenChargeMapExtractor,
    SerperExtractor,
    OSMExtractor,
)
from engine.ingestion.deduplication import compute_content_hash


DEFAULT_EXTRACTOR_REGISTRY: Dict[str, Callable[[], Any]] = {
    "google_places": GooglePlacesExtractor,
    "sport_scotland": SportScotlandExtractor,
    "edinburgh_council": EdinburghCouncilExtractor,
    "open_charge_map": OpenChargeMapExtractor,
    "serper": SerperExtractor,
    "openstreetmap": OSMExtractor,
}


def now_utc() -> datetime:
    """Get current time as timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def _safe_json_dumps(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except TypeError:
        return json.dumps({"detail": str(value)})


def load_raw_payload(file_path: str) -> Any:
    """Load a raw ingestion payload from disk."""
    with open(file_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _get_items_for_source(source: str, payload: Any) -> List[Any]:
    if source == "google_places":
        if isinstance(payload, dict):
            return payload.get("places", [])
        return []
    if source == "open_charge_map":
        return payload if isinstance(payload, list) else []
    if source in {"sport_scotland", "edinburgh_council"}:
        if isinstance(payload, dict):
            return payload.get("features", [])
        return []
    if source in {"serper", "openstreetmap"}:
        return [payload] if payload else []
    return []


def _get_item_id(source: str, item: Any) -> Optional[str]:
    if not isinstance(item, dict):
        return None
    if source == "google_places":
        return item.get("id")
    if source == "open_charge_map":
        return item.get("UUID")
    if source == "sport_scotland":
        return item.get("id")
    if source == "edinburgh_council":
        properties = item.get("properties", {})
        return item.get("id") or properties.get("OBJECTID") or properties.get("FID")
    return None


def _normalize_external_ids(extracted: Dict[str, Any], source: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    normalized = dict(extracted)
    external_ids = normalized.pop("external_ids", {}) or {}
    external_id = normalized.pop("external_id", None)

    if not isinstance(external_ids, dict):
        external_ids = {}

    if external_id:
        external_ids[source] = external_id

    return normalized, external_ids


class RetryableExtractionError(Exception):
    """Exception raised when a retry attempt fails."""

    def __init__(self, message: str, error_details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_details = error_details


@dataclass
class RetrySummary:
    retried: int
    succeeded: int
    failed: int


async def record_failed_extraction(
    db: Prisma,
    raw_ingestion_id: str,
    source: str,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None,
    increment_retry: bool = False,
) -> Any:
    """Create or update a FailedExtraction record."""
    details_json = _safe_json_dumps(error_details)
    existing = await db.failedextraction.find_first(
        where={
            "raw_ingestion_id": raw_ingestion_id,
            "source": source,
        }
    )

    if existing:
        data: Dict[str, Any] = {
            "error_message": error_message,
            "last_attempt_at": now_utc(),
        }
        if details_json is not None:
            data["error_details"] = details_json
        if increment_retry:
            data["retry_count"] = existing.retry_count + 1
        return await db.failedextraction.update(where={"id": existing.id}, data=data)

    retry_count = 1 if increment_retry else 0
    return await db.failedextraction.create(
        data={
            "raw_ingestion_id": raw_ingestion_id,
            "source": source,
            "error_message": error_message,
            "error_details": details_json,
            "retry_count": retry_count,
            "last_attempt_at": now_utc(),
        }
    )


async def list_retryable_failures(
    db: Prisma,
    max_retries: int,
    limit: Optional[int] = None,
) -> List[Any]:
    """Fetch FailedExtraction records eligible for retry."""
    query = {
        "where": {"retry_count": {"lt": max_retries}}
    }
    if limit is not None:
        query["take"] = limit
    return await db.failedextraction.find_many(**query)


def _build_extraction_hash(
    raw_ingestion_id: str,
    source: str,
    attributes: Dict[str, Any],
    discovered_attributes: Dict[str, Any],
    external_ids: Dict[str, Any],
) -> str:
    payload = {
        "raw_ingestion_id": raw_ingestion_id,
        "source": source,
        "attributes": attributes,
        "discovered_attributes": discovered_attributes,
        "external_ids": external_ids,
    }
    return compute_content_hash(payload)


async def _save_extracted_listing(
    db: Prisma,
    raw_ingestion_id: str,
    source: str,
    entity_type: str,
    attributes: Dict[str, Any],
    discovered_attributes: Dict[str, Any],
    external_ids: Dict[str, Any],
    model_used: Optional[str],
) -> Any:
    extraction_hash = _build_extraction_hash(
        raw_ingestion_id,
        source,
        attributes,
        discovered_attributes,
        external_ids,
    )

    data = {
        "raw_ingestion_id": raw_ingestion_id,
        "source": source,
        "entity_type": entity_type,
        "attributes": _safe_json_dumps(attributes),
        "discovered_attributes": _safe_json_dumps(discovered_attributes),
        "external_ids": _safe_json_dumps(external_ids),
        "extraction_hash": extraction_hash,
    }

    if model_used:
        data["model_used"] = model_used

    return await db.extractedlisting.create(data=data)


class ExtractionRetryHandler:
    """Retry handler that re-runs extraction for FailedExtraction records."""

    def __init__(
        self,
        db: Prisma,
        extractor_registry: Optional[Dict[str, Any]] = None,
        payload_loader: Optional[Callable[[str], Any]] = None,
    ):
        self.db = db
        self.extractor_registry = extractor_registry or DEFAULT_EXTRACTOR_REGISTRY
        self.payload_loader = payload_loader or load_raw_payload

    def _get_extractor(self, source: str) -> Any:
        factory = self.extractor_registry.get(source)
        if factory is None:
            raise RetryableExtractionError(
                "No extractor registered for source",
                {"source": source},
            )

        if isinstance(factory, type):
            return factory()

        return factory

    def _get_model_used(self, extractor: Any) -> Optional[str]:
        llm_client = getattr(extractor, "llm_client", None)
        if llm_client and hasattr(llm_client, "model_name"):
            return llm_client.model_name
        return None

    async def retry(self, failure: Any) -> bool:
        raw_record = await self.db.rawingestion.find_unique(
            where={"id": failure.raw_ingestion_id}
        )
        if raw_record is None:
            raise RetryableExtractionError(
                "RawIngestion record not found",
                {"raw_ingestion_id": failure.raw_ingestion_id},
            )

        payload = self.payload_loader(raw_record.file_path)
        items = _get_items_for_source(failure.source, payload)
        if not items:
            raise RetryableExtractionError(
                "No extractable items found in payload",
                {"source": failure.source},
            )

        extractor = self._get_extractor(failure.source)
        model_used = self._get_model_used(extractor)

        failures: List[Dict[str, Any]] = []
        success_count = 0

        for index, item in enumerate(items):
            try:
                extracted = extractor.extract(item)
                validated = extractor.validate(extracted)
                normalized, external_ids = _normalize_external_ids(validated, failure.source)
                attributes, discovered = extractor.split_attributes(normalized)

                entity_type = normalized.get("entity_type")
                if not entity_type:
                    raise ValueError("Missing required field: entity_type")

                await _save_extracted_listing(
                    self.db,
                    raw_record.id,
                    failure.source,
                    entity_type,
                    attributes,
                    discovered,
                    external_ids,
                    model_used,
                )

                success_count += 1

            except Exception as exc:
                failures.append(
                    {
                        "index": index,
                        "item_id": _get_item_id(failure.source, item),
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    }
                )

        if failures:
            raise RetryableExtractionError(
                "One or more items failed extraction",
                {
                    "success_count": success_count,
                    "failure_count": len(failures),
                    "failed_items": failures,
                },
            )

        return True


async def retry_failed_extractions(
    db: Prisma,
    max_retries: int = 3,
    limit: Optional[int] = None,
    retry_handler: Optional[Callable[[Any], Any]] = None,
) -> Dict[str, int]:
    """Retry failed extractions and update FailedExtraction records."""
    failures = await list_retryable_failures(db, max_retries, limit)
    if retry_handler is None:
        retry_handler = ExtractionRetryHandler(db).retry

    summary = RetrySummary(retried=0, succeeded=0, failed=0)

    for failure in failures:
        summary.retried += 1
        try:
            result = await retry_handler(failure)
            if result is True:
                await db.failedextraction.delete(where={"id": failure.id})
                summary.succeeded += 1
            else:
                raise RetryableExtractionError("Retry failed without success")
        except RetryableExtractionError as exc:
            await db.failedextraction.update(
                where={"id": failure.id},
                data={
                    "retry_count": failure.retry_count + 1,
                    "error_message": str(exc),
                    "error_details": _safe_json_dumps(exc.error_details),
                    "last_attempt_at": now_utc(),
                },
            )
            summary.failed += 1
        except Exception as exc:
            await db.failedextraction.update(
                where={"id": failure.id},
                data={
                    "retry_count": failure.retry_count + 1,
                    "error_message": str(exc),
                    "error_details": _safe_json_dumps(
                        {"error_type": type(exc).__name__, "message": str(exc)}
                    ),
                    "last_attempt_at": now_utc(),
                },
            )
            summary.failed += 1

    return {
        "retried": summary.retried,
        "succeeded": summary.succeeded,
        "failed": summary.failed,
    }
