"""
Structured logging configuration for extraction engine.

Provides JSON-formatted logging with contextual fields (source, extractor, record_id)
and extraction-specific helpers for logging metadata (duration, tokens, fields, confidence).
"""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TextIO


class ExtractionLogFormatter(logging.Formatter):
    """
    Custom JSON formatter for extraction logs.

    Outputs structured JSON with:
    - Standard fields: timestamp, level, message, logger_name
    - Contextual fields: source, extractor, record_id (if present)
    - Exception info: exception traceback (if present)
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.

        Args:
            record: LogRecord to format

        Returns:
            JSON string with log data
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add contextual fields if present
        for field in ["source", "extractor", "record_id", "operation"]:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        # Add extraction metadata if present
        for field in [
            "duration_seconds",
            "fields_extracted",
            "confidence_score",
            "model",
            "tokens_in",
            "tokens_out",
            "tokens_total",
            "cost_usd",
            "error",
            "field",
        ]:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


# Global logger instance
_extraction_logger: Optional[logging.Logger] = None


def setup_extraction_logger(
    stream: Optional[TextIO] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Setup and configure the extraction logger.

    Creates a logger with JSON formatter and stream handler.

    Args:
        stream: Output stream (default: sys.stdout)
        level: Log level (default: INFO)

    Returns:
        Configured logger instance
    """
    global _extraction_logger

    logger = logging.getLogger("extraction")
    logger.setLevel(level)
    logger.propagate = False

    # Remove existing handlers
    logger.handlers = []

    # Create handler with JSON formatter
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(ExtractionLogFormatter())
    logger.addHandler(handler)

    _extraction_logger = logger
    return logger


def get_extraction_logger() -> logging.Logger:
    """
    Get the configured extraction logger.

    If logger hasn't been setup, initializes with defaults.

    Returns:
        Extraction logger instance
    """
    global _extraction_logger

    if _extraction_logger is None:
        setup_extraction_logger()

    return _extraction_logger


def log_extraction_start(
    logger: logging.Logger,
    source: str,
    record_id: str,
    extractor: str,
) -> None:
    """
    Log the start of an extraction operation.

    Args:
        logger: Logger instance
        source: Data source name
        record_id: Raw ingestion record ID
        extractor: Extractor class name
    """
    logger.info(
        "Starting extraction",
        extra={
            "source": source,
            "record_id": record_id,
            "extractor": extractor,
        }
    )


def log_extraction_success(
    logger: logging.Logger,
    source: str,
    record_id: str,
    extractor: str,
    duration_seconds: float,
    fields_extracted: int,
    confidence_score: Optional[float] = None,
) -> None:
    """
    Log a successful extraction operation.

    Args:
        logger: Logger instance
        source: Data source name
        record_id: Raw ingestion record ID
        extractor: Extractor class name
        duration_seconds: Extraction duration in seconds
        fields_extracted: Number of fields extracted
        confidence_score: Optional confidence score (0-1)
    """
    extra = {
        "source": source,
        "record_id": record_id,
        "extractor": extractor,
        "duration_seconds": duration_seconds,
        "fields_extracted": fields_extracted,
    }

    if confidence_score is not None:
        extra["confidence_score"] = confidence_score

    logger.info("Extraction successful", extra=extra)


def log_extraction_failure(
    logger: logging.Logger,
    source: str,
    record_id: str,
    extractor: str,
    error: str,
    duration_seconds: float,
) -> None:
    """
    Log a failed extraction operation.

    Args:
        logger: Logger instance
        source: Data source name
        record_id: Raw ingestion record ID
        extractor: Extractor class name
        error: Error message
        duration_seconds: Extraction duration before failure
    """
    logger.error(
        "Extraction failed",
        extra={
            "source": source,
            "record_id": record_id,
            "extractor": extractor,
            "error": error,
            "duration_seconds": duration_seconds,
        }
    )


def log_llm_call(
    logger: logging.Logger,
    source: str,
    record_id: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    duration_seconds: float,
    cost_usd: float,
) -> None:
    """
    Log an LLM API call with cost metadata.

    Args:
        logger: Logger instance
        source: Data source name
        record_id: Raw ingestion record ID
        model: LLM model identifier
        tokens_in: Input tokens
        tokens_out: Output tokens
        duration_seconds: API call duration
        cost_usd: Estimated cost in USD
    """
    logger.info(
        "LLM call completed",
        extra={
            "source": source,
            "record_id": record_id,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_total": tokens_in + tokens_out,
            "duration_seconds": duration_seconds,
            "cost_usd": cost_usd,
        }
    )
