"""
Tests for structured logging configuration in extraction engine.

Tests cover:
- JSON formatter setup
- Contextual fields (source, extractor, record_id)
- Log levels (info, warning, error)
- Extraction metadata logging (duration, tokens, fields)
"""

import json
import logging
from io import StringIO
from datetime import datetime

import pytest

from engine.extraction.logging_config import (
    setup_extraction_logger,
    get_extraction_logger,
    ExtractionLogFormatter,
    log_extraction_start,
    log_extraction_success,
    log_extraction_failure,
    log_llm_call,
)


class TestExtractionLogFormatter:
    """Test JSON log formatter."""

    def test_formats_as_json(self):
        """Test that formatter outputs valid JSON."""
        formatter = ExtractionLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"
        assert "timestamp" in parsed

    def test_includes_contextual_fields(self):
        """Test that formatter includes extra fields."""
        formatter = ExtractionLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.source = "google_places"
        record.extractor = "GooglePlacesExtractor"
        record.record_id = "test-uuid-123"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["source"] == "google_places"
        assert parsed["extractor"] == "GooglePlacesExtractor"
        assert parsed["record_id"] == "test-uuid-123"

    def test_handles_exception_info(self):
        """Test that formatter includes exception info."""
        import sys
        formatter = ExtractionLogFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

            output = formatter.format(record)
            parsed = json.loads(output)

            assert parsed["level"] == "ERROR"
            assert "exception" in parsed
            assert "ValueError: Test error" in parsed["exception"]


class TestLoggerSetup:
    """Test logger configuration."""

    def test_setup_logger_creates_json_handler(self):
        """Test that setup creates a handler with JSON formatter."""
        stream = StringIO()
        logger = setup_extraction_logger(stream=stream)

        logger.info("Test message")

        output = stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"

    def test_get_logger_returns_configured_logger(self):
        """Test that get_extraction_logger returns the same logger."""
        logger1 = get_extraction_logger()
        logger2 = get_extraction_logger()

        assert logger1 is logger2
        assert logger1.name == "extraction"

    def test_logger_accepts_different_log_levels(self):
        """Test that logger handles different log levels."""
        stream = StringIO()
        logger = setup_extraction_logger(stream=stream, level=logging.DEBUG)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        output = stream.getvalue()
        lines = [line for line in output.strip().split('\n') if line]

        assert len(lines) == 4

        parsed = [json.loads(line) for line in lines]
        assert parsed[0]["level"] == "DEBUG"
        assert parsed[1]["level"] == "INFO"
        assert parsed[2]["level"] == "WARNING"
        assert parsed[3]["level"] == "ERROR"


class TestExtractionLogging:
    """Test extraction-specific logging helpers."""

    def test_log_extraction_start(self):
        """Test logging extraction start with context."""
        stream = StringIO()
        logger = setup_extraction_logger(stream=stream)

        log_extraction_start(
            logger=logger,
            source="google_places",
            record_id="uuid-123",
            extractor="GooglePlacesExtractor",
        )

        output = stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["message"] == "Starting extraction"
        assert parsed["source"] == "google_places"
        assert parsed["record_id"] == "uuid-123"
        assert parsed["extractor"] == "GooglePlacesExtractor"
        assert parsed["level"] == "INFO"

    def test_log_extraction_success(self):
        """Test logging successful extraction with metadata."""
        stream = StringIO()
        logger = setup_extraction_logger(stream=stream)

        log_extraction_success(
            logger=logger,
            source="google_places",
            record_id="uuid-123",
            extractor="GooglePlacesExtractor",
            duration_seconds=2.5,
            fields_extracted=15,
            confidence_score=0.95,
        )

        output = stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["message"] == "Extraction successful"
        assert parsed["source"] == "google_places"
        assert parsed["duration_seconds"] == 2.5
        assert parsed["fields_extracted"] == 15
        assert parsed["confidence_score"] == 0.95
        assert parsed["level"] == "INFO"

    def test_log_extraction_failure(self):
        """Test logging extraction failure with error details."""
        stream = StringIO()
        logger = setup_extraction_logger(stream=stream)

        log_extraction_failure(
            logger=logger,
            source="serper",
            record_id="uuid-456",
            extractor="SerperExtractor",
            error="LLM timeout after 3 retries",
            duration_seconds=10.2,
        )

        output = stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["message"] == "Extraction failed"
        assert parsed["source"] == "serper"
        assert parsed["error"] == "LLM timeout after 3 retries"
        assert parsed["duration_seconds"] == 10.2
        assert parsed["level"] == "ERROR"

    def test_log_llm_call(self):
        """Test logging LLM API calls with cost metadata."""
        stream = StringIO()
        logger = setup_extraction_logger(stream=stream)

        log_llm_call(
            logger=logger,
            source="osm",
            record_id="uuid-789",
            model="claude-3-haiku-20240307",
            tokens_in=500,
            tokens_out=200,
            duration_seconds=1.8,
            cost_usd=0.00025,
        )

        output = stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["message"] == "LLM call completed"
        assert parsed["model"] == "claude-3-haiku-20240307"
        assert parsed["tokens_in"] == 500
        assert parsed["tokens_out"] == 200
        assert parsed["tokens_total"] == 700
        assert parsed["duration_seconds"] == 1.8
        assert parsed["cost_usd"] == 0.00025
        assert parsed["level"] == "INFO"

    def test_log_extraction_with_null_fields(self):
        """Test logging handles null/missing fields gracefully."""
        stream = StringIO()
        logger = setup_extraction_logger(stream=stream)

        log_extraction_success(
            logger=logger,
            source="serper",
            record_id="uuid-null",
            extractor="SerperExtractor",
            duration_seconds=1.2,
            fields_extracted=8,
            confidence_score=None,  # No confidence for this extractor
        )

        output = stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["fields_extracted"] == 8
        # confidence_score should not be present when it's None
        assert "confidence_score" not in parsed

    def test_log_extraction_with_warnings(self):
        """Test logging warnings during extraction."""
        stream = StringIO()
        logger = setup_extraction_logger(stream=stream)

        # Simulate warning during extraction
        logger.warning(
            "Missing required field",
            extra={
                "source": "sport_scotland",
                "record_id": "uuid-warn",
                "field": "postcode",
            }
        )

        output = stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["level"] == "WARNING"
        assert parsed["message"] == "Missing required field"
        assert parsed["field"] == "postcode"


class TestExtractWithLogging:
    """Test extract_with_logging wrapper method."""

    def test_extract_with_logging_success(self):
        """Test successful extraction logs correctly."""
        from io import StringIO
        from engine.extraction.base import BaseExtractor

        # Create a simple test extractor
        class TestExtractor(BaseExtractor):
            @property
            def source_name(self) -> str:
                return "test_source"

            def extract(self, raw_data):
                return {
                    "entity_name": "Test Venue",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                }

            def validate(self, extracted):
                return extracted

            def split_attributes(self, extracted):
                return extracted, {}

        stream = StringIO()
        logger = setup_extraction_logger(stream=stream)

        extractor = TestExtractor()
        result = extractor.extract_with_logging(
            raw_data={"name": "Test"},
            record_id="test-uuid-123",
        )

        # Verify result
        assert result["entity_name"] == "Test Venue"

        # Verify logging
        output = stream.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        assert len(lines) == 2  # Start and success

        start_log = json.loads(lines[0])
        assert start_log["message"] == "Starting extraction"
        assert start_log["source"] == "test_source"

        success_log = json.loads(lines[1])
        assert success_log["message"] == "Extraction successful"
        assert success_log["fields_extracted"] == 3

    def test_extract_with_logging_failure(self):
        """Test failed extraction logs correctly."""
        from io import StringIO
        from engine.extraction.base import BaseExtractor

        class FailingExtractor(BaseExtractor):
            @property
            def source_name(self) -> str:
                return "failing_source"

            def extract(self, raw_data):
                raise ValueError("Test extraction error")

            def validate(self, extracted):
                return extracted

            def split_attributes(self, extracted):
                return extracted, {}

        stream = StringIO()
        logger = setup_extraction_logger(stream=stream)

        extractor = FailingExtractor()

        with pytest.raises(ValueError):
            extractor.extract_with_logging(
                raw_data={},
                record_id="fail-uuid",
            )

        # Verify error was logged
        output = stream.getvalue()
        lines = [line for line in output.strip().split('\n') if line]
        assert len(lines) == 2  # Start and failure

        failure_log = json.loads(lines[1])
        assert failure_log["message"] == "Extraction failed"
        assert failure_log["level"] == "ERROR"
        assert failure_log["error"] == "Test extraction error"


class TestLoggingIntegration:
    """Test logging integration with extractors."""

    def test_logger_can_be_used_in_context_manager(self):
        """Test logger works with context managers for timing."""
        stream = StringIO()
        logger = setup_extraction_logger(stream=stream)

        import time

        start = time.time()
        logger.info("Operation started", extra={"operation": "test"})
        time.sleep(0.01)  # Simulate work
        duration = time.time() - start

        logger.info(
            "Operation completed",
            extra={
                "operation": "test",
                "duration_seconds": round(duration, 3),
            }
        )

        output = stream.getvalue()
        lines = [line for line in output.strip().split('\n') if line]

        assert len(lines) == 2
        parsed_end = json.loads(lines[1])
        assert parsed_end["duration_seconds"] >= 0.01

    def test_multiple_extractors_log_independently(self):
        """Test that different extractors can log with different context."""
        stream = StringIO()
        logger = setup_extraction_logger(stream=stream)

        # Simulate two extractors logging
        log_extraction_start(
            logger=logger,
            source="google_places",
            record_id="uuid-1",
            extractor="GooglePlacesExtractor",
        )

        log_extraction_start(
            logger=logger,
            source="osm",
            record_id="uuid-2",
            extractor="OSMExtractor",
        )

        output = stream.getvalue()
        lines = [line for line in output.strip().split('\n') if line]

        assert len(lines) == 2
        parsed = [json.loads(line) for line in lines]

        assert parsed[0]["source"] == "google_places"
        assert parsed[1]["source"] == "osm"
