"""Tests for extraction quarantine and retry workflow."""

import json
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock


class TestQuarantineImports(unittest.TestCase):
    """Test quarantine module imports."""

    def test_quarantine_module_imports(self):
        try:
            from engine.extraction.quarantine import (
                record_failed_extraction,
                list_retryable_failures,
                retry_failed_extractions,
                RetryableExtractionError,
                ExtractionRetryHandler,
            )
            self.assertTrue(callable(record_failed_extraction))
            self.assertTrue(callable(list_retryable_failures))
            self.assertTrue(callable(retry_failed_extractions))
            self.assertTrue(issubclass(RetryableExtractionError, Exception))
            self.assertTrue(callable(ExtractionRetryHandler))
        except ImportError as exc:
            self.fail(f"Failed to import quarantine utilities: {exc}")


class TestRecordFailedExtraction(unittest.IsolatedAsyncioTestCase):
    """Test FailedExtraction creation and updates."""

    async def test_record_failed_extraction_creates_record(self):
        from engine.extraction.quarantine import record_failed_extraction

        db = AsyncMock()
        db.failedextraction.find_first = AsyncMock(return_value=None)
        db.failedextraction.create = AsyncMock(return_value=SimpleNamespace(id="fail-1"))

        await record_failed_extraction(
            db,
            raw_ingestion_id="raw-1",
            source="google_places",
            error_message="Missing entity_name",
            error_details={"detail": "displayName missing"},
        )

        call_data = db.failedextraction.create.call_args.kwargs["data"]
        self.assertEqual(call_data["raw_ingestion_id"], "raw-1")
        self.assertEqual(call_data["source"], "google_places")
        self.assertEqual(call_data["retry_count"], 0)
        self.assertIsInstance(call_data["last_attempt_at"], datetime)
        self.assertIn("error_details", call_data)

    async def test_record_failed_extraction_updates_retry_count(self):
        from engine.extraction.quarantine import record_failed_extraction

        existing = SimpleNamespace(id="fail-2", retry_count=2)
        db = AsyncMock()
        db.failedextraction.find_first = AsyncMock(return_value=existing)
        db.failedextraction.update = AsyncMock(return_value=existing)

        await record_failed_extraction(
            db,
            raw_ingestion_id="raw-2",
            source="serper",
            error_message="Timeout",
            error_details={"error_type": "TimeoutError"},
            increment_retry=True,
        )

        update_data = db.failedextraction.update.call_args.kwargs["data"]
        self.assertEqual(update_data["retry_count"], 3)
        self.assertIn("error_details", update_data)


class TestListRetryableFailures(unittest.IsolatedAsyncioTestCase):
    """Test retryable failure query."""

    async def test_list_retryable_failures_filters_by_retry_count(self):
        from engine.extraction.quarantine import list_retryable_failures

        db = AsyncMock()
        db.failedextraction.find_many = AsyncMock(return_value=[])

        await list_retryable_failures(db, max_retries=3, limit=5)

        kwargs = db.failedextraction.find_many.call_args.kwargs
        self.assertEqual(kwargs["where"]["retry_count"]["lt"], 3)
        self.assertEqual(kwargs["take"], 5)


class TestRetryFailedExtractions(unittest.IsolatedAsyncioTestCase):
    """Test retry workflow updates and deletes records."""

    async def test_retry_failed_extractions_updates_records(self):
        from engine.extraction.quarantine import retry_failed_extractions, RetryableExtractionError

        db = AsyncMock()
        failure1 = SimpleNamespace(id="f1", raw_ingestion_id="r1", source="google_places", retry_count=0)
        failure2 = SimpleNamespace(id="f2", raw_ingestion_id="r2", source="google_places", retry_count=1)

        db.failedextraction.find_many = AsyncMock(return_value=[failure1, failure2])
        db.failedextraction.delete = AsyncMock()
        db.failedextraction.update = AsyncMock()

        async def handler(failure):
            if failure.id == "f1":
                return True
            raise RetryableExtractionError("timeout", {"error_type": "TimeoutError"})

        summary = await retry_failed_extractions(db, max_retries=3, retry_handler=handler)

        self.assertEqual(summary["retried"], 2)
        self.assertEqual(summary["succeeded"], 1)
        self.assertEqual(summary["failed"], 1)

        delete_kwargs = db.failedextraction.delete.call_args.kwargs
        self.assertEqual(delete_kwargs["where"]["id"], "f1")

        update_kwargs = db.failedextraction.update.call_args.kwargs
        self.assertEqual(update_kwargs["where"]["id"], "f2")
        self.assertEqual(update_kwargs["data"]["retry_count"], 2)


class TestExtractionRetryHandlerInvalidData(unittest.IsolatedAsyncioTestCase):
    """Test quarantine behavior with invalid fixture data."""

    async def test_invalid_google_places_payload_is_quarantined(self):
        from engine.extraction.quarantine import ExtractionRetryHandler, RetryableExtractionError
        from engine.extraction.extractors import GooglePlacesExtractor

        fixture_path = Path(__file__).parent / "fixtures" / "google_places_venue_response.json"
        with open(fixture_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        payload["places"][0].pop("displayName", None)

        db = AsyncMock()
        db.rawingestion.find_unique = AsyncMock(
            return_value=SimpleNamespace(id="raw-1", source="google_places", file_path="dummy.json")
        )
        db.extractedlisting.create = AsyncMock()

        handler = ExtractionRetryHandler(
            db,
            extractor_registry={"google_places": GooglePlacesExtractor},
            payload_loader=lambda _: payload,
        )

        failure = SimpleNamespace(id="fail-1", raw_ingestion_id="raw-1", source="google_places", retry_count=0)

        with self.assertRaises(RetryableExtractionError) as ctx:
            await handler.retry(failure)

        details = ctx.exception.error_details
        self.assertEqual(details["failure_count"], 1)
        self.assertEqual(details["failed_items"][0]["error_type"], "ValueError")
        self.assertEqual(details["failed_items"][0]["item_id"], "ChIJhwNDsAjFh0gRDARGLR5vtdI")
        db.extractedlisting.create.assert_not_called()


class TestExtractionRetryHandlerTimeout(unittest.IsolatedAsyncioTestCase):
    """Test timeout failures are captured for retries."""

    async def test_timeout_failure_is_quarantined(self):
        from engine.extraction.quarantine import ExtractionRetryHandler, RetryableExtractionError

        class TimeoutExtractor:
            @property
            def source_name(self):
                return "serper"

            def extract(self, raw_data):
                raise TimeoutError("LLM timeout")

            def validate(self, extracted):
                return extracted

            def split_attributes(self, extracted):
                return {}, {}

        db = AsyncMock()
        db.rawingestion.find_unique = AsyncMock(
            return_value=SimpleNamespace(id="raw-2", source="serper", file_path="dummy.json")
        )
        db.extractedlisting.create = AsyncMock()

        handler = ExtractionRetryHandler(
            db,
            extractor_registry={"serper": TimeoutExtractor()},
            payload_loader=lambda _: {"organic": []},
        )

        failure = SimpleNamespace(id="fail-2", raw_ingestion_id="raw-2", source="serper", retry_count=0)

        with self.assertRaises(RetryableExtractionError) as ctx:
            await handler.retry(failure)

        details = ctx.exception.error_details
        self.assertEqual(details["failed_items"][0]["error_type"], "TimeoutError")


if __name__ == "__main__":
    unittest.main()
