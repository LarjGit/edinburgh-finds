"""
Structured Logging Infrastructure for Ingestion Pipeline

This module provides structured logging capabilities for data source connectors,
enabling consistent, contextual, and parseable log output across the ingestion
pipeline.

Key Features:
- Source-specific logging with automatic context inclusion
- Event-based logging methods (fetch, save, deduplication events)
- Structured output (supports JSON format)
- Log level filtering (DEBUG, INFO, WARNING, ERROR)
- Timestamp inclusion (ISO 8601 format)
- Integration with standard Python logging

Usage:
    from engine.ingestion.logging_config import IngestionLogger

    logger = IngestionLogger(source="serper")
    logger.log_fetch_start(query="padel edinburgh")
    # ... perform fetch ...
    logger.log_fetch_success(query="padel edinburgh", record_count=10)
"""

import logging
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import traceback as tb


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured log records.

    Formats log records with consistent structure including:
    - ISO 8601 timestamp
    - Log level
    - Source identifier
    - Event type
    - Additional context fields
    """

    def __init__(self, format_type: str = "text"):
        """
        Initialize formatter.

        Args:
            format_type: Output format - "text" or "json"
        """
        super().__init__()
        self.format_type = format_type

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record.

        Args:
            record: Log record to format

        Returns:
            Formatted log string
        """
        # Extract custom fields from record
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "source": getattr(record, "source", "unknown"),
            "event": getattr(record, "event", "log"),
            "message": record.getMessage(),
        }

        # Add any extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        if self.format_type == "json":
            return json.dumps(log_data)
        else:
            # Text format: timestamp [LEVEL] source:event - message {extras}
            extras = {k: v for k, v in log_data.items()
                     if k not in ["timestamp", "level", "source", "event", "message"]}
            extras_str = f" {json.dumps(extras)}" if extras else ""
            return (
                f"{log_data['timestamp']} "
                f"[{log_data['level']}] "
                f"{log_data['source']}:{log_data['event']} - "
                f"{log_data['message']}"
                f"{extras_str}"
            )


class IngestionLogger:
    """
    Structured logger for data ingestion connectors.

    Provides convenient methods for logging common ingestion events with
    consistent structure and contextual information.

    Attributes:
        source: Identifier for the data source (e.g., "serper", "google_places")
        logger: Underlying Python logger instance
    """

    def __init__(
        self,
        source: str,
        level: int = logging.INFO,
        format: str = "text"
    ):
        """
        Initialize logger for a specific data source.

        Args:
            source: Data source identifier (e.g., "serper", "google_places")
            level: Logging level (default: logging.INFO)
            format: Output format - "text" or "json" (default: "text")
        """
        self.source = source
        self.format = format

        # Create logger with source-specific name
        self.logger = logging.getLogger(f"ingestion.{source}")
        self.logger.setLevel(level)

        # Remove any existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Add structured formatter
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter(format_type=format))
        self.logger.addHandler(handler)

        # Prevent propagation to root logger to avoid duplicate logs
        self.logger.propagate = False

    def _log(
        self,
        level: int,
        event: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Internal method to log with structured context.

        Args:
            level: Log level (INFO, WARNING, ERROR, etc.)
            event: Event type identifier
            message: Log message
            extra: Additional context fields
        """
        # Include timestamp in message for default formatters (like assertLogs)
        timestamp = datetime.now(timezone.utc).isoformat()

        # Build message with extras for default formatter
        extras_str = ""
        if extra:
            # Include select extra fields in the message
            extras_parts = []
            for key, value in extra.items():
                if key not in ["query", "source_url", "file_path"]:  # Already in main message
                    extras_parts.append(f"{key}={value}")
            if extras_parts:
                extras_str = " " + " ".join(extras_parts)

        full_message = f"{timestamp} {message}{extras_str}"

        # Create extra dict for LogRecord
        extra_dict = {
            "source": self.source,
            "event": event,
        }

        if extra:
            extra_dict["extra_fields"] = extra

        self.logger.log(level, full_message, extra=extra_dict)

    def log_fetch_start(self, query: str, extra: Optional[Dict[str, Any]] = None):
        """
        Log the start of a fetch operation.

        Args:
            query: Search query or identifier being fetched
            extra: Additional context fields
        """
        extra_data = {"query": query}
        if extra:
            extra_data.update(extra)

        self._log(
            logging.INFO,
            "fetch_start",
            f"[fetch_start] Starting fetch for query: {query}",
            extra_data
        )

    def log_fetch_success(
        self,
        query: str,
        record_count: int,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Log successful fetch operation.

        Args:
            query: Search query or identifier that was fetched
            record_count: Number of records fetched
            extra: Additional context fields
        """
        extra_data = {"query": query, "record_count": record_count}
        if extra:
            extra_data.update(extra)

        self._log(
            logging.INFO,
            "fetch_success",
            f"[fetch_success] Successfully fetched {record_count} records for query: {query}",
            extra_data
        )

    def log_fetch_error(
        self,
        query: str,
        error: Exception,
        include_traceback: bool = False,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Log fetch operation error.

        Args:
            query: Search query or identifier that failed
            error: Exception that occurred
            include_traceback: Whether to include full traceback
            extra: Additional context fields
        """
        extra_data = {
            "query": query,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }

        if include_traceback:
            extra_data["traceback"] = tb.format_exc()

        if extra:
            extra_data.update(extra)

        self._log(
            logging.ERROR,
            "fetch_error",
            f"[fetch_error] Fetch failed for query '{query}': {error}",
            extra_data
        )

    def log_save_start(self, source_url: str, extra: Optional[Dict[str, Any]] = None):
        """
        Log the start of a save operation.

        Args:
            source_url: URL or identifier of the source being saved
            extra: Additional context fields
        """
        extra_data = {"source_url": source_url}
        if extra:
            extra_data.update(extra)

        self._log(
            logging.INFO,
            "save_start",
            f"[save_start] Starting save for source: {source_url}",
            extra_data
        )

    def log_save_success(
        self,
        file_path: str,
        source_url: str,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Log successful save operation.

        Args:
            file_path: Path where data was saved
            source_url: URL or identifier of the source
            extra: Additional context fields
        """
        extra_data = {"file_path": file_path, "source_url": source_url}
        if extra:
            extra_data.update(extra)

        self._log(
            logging.INFO,
            "save_success",
            f"[save_success] Successfully saved to {file_path}",
            extra_data
        )

    def log_save_error(
        self,
        source_url: str,
        error: Exception,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Log save operation error.

        Args:
            source_url: URL or identifier of the source
            error: Exception that occurred
            extra: Additional context fields
        """
        extra_data = {
            "source_url": source_url,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }

        if extra:
            extra_data.update(extra)

        self._log(
            logging.ERROR,
            "save_error",
            f"[save_error] Save failed for source '{source_url}': {error}",
            extra_data
        )

    def log_duplicate_detected(
        self,
        content_hash: str,
        source_url: str,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Log when duplicate content is detected.

        Args:
            content_hash: Hash of the duplicate content
            source_url: URL or identifier of the source
            extra: Additional context fields
        """
        extra_data = {"content_hash": content_hash, "source_url": source_url}
        if extra:
            extra_data.update(extra)

        self._log(
            logging.INFO,
            "duplicate_detected",
            f"[duplicate_detected] Duplicate content detected (hash: {content_hash[:8]}...)",
            extra_data
        )

    def log_debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """
        Log debug message.

        Args:
            message: Debug message
            extra: Additional context fields
        """
        self._log(
            logging.DEBUG,
            "debug",
            message,
            extra
        )


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format: str = "text"
):
    """
    Configure global logging for the ingestion pipeline.

    This function sets up the root logger for the ingestion module with
    consistent formatting and output destinations.

    Args:
        level: Global log level (default: logging.INFO)
        log_file: Optional file path for log output
        format: Output format - "text" or "json" (default: "text")

    Example:
        # Configure to log to file
        configure_logging(
            level=logging.DEBUG,
            log_file="engine/logs/ingestion.log",
            format="json"
        )
    """
    # Get or create the ingestion logger
    logger = logging.getLogger("ingestion")
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = StructuredFormatter(format_type=format)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        import os
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root
    logger.propagate = False
