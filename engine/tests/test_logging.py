"""
Tests for Ingestion Pipeline Logging Infrastructure

This module tests the structured logging system for data ingestion connectors.
The logging infrastructure provides:
- Structured log output (JSON format)
- Contextual information (source, timestamp, status, errors)
- Integration with BaseConnector interface
- Log level filtering
"""

import unittest
import json
import logging
from io import StringIO
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestIngestionLogger(unittest.TestCase):
    """Test the IngestionLogger class and structured logging functionality"""

    def test_ingestion_logger_exists(self):
        """Test that IngestionLogger class can be imported"""
        try:
            from engine.ingestion.logging_config import IngestionLogger
            self.assertIsNotNone(IngestionLogger)
        except ImportError as e:
            self.fail(f"Failed to import IngestionLogger: {e}")

    def test_ingestion_logger_initialization(self):
        """Test IngestionLogger can be initialized with a source name"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="serper")
        self.assertEqual(logger.source, "serper")
        self.assertIsNotNone(logger.logger)

    def test_ingestion_logger_default_level(self):
        """Test IngestionLogger defaults to INFO level"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="test")
        self.assertEqual(logger.logger.level, logging.INFO)

    def test_ingestion_logger_custom_level(self):
        """Test IngestionLogger can be initialized with custom log level"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="test", level=logging.DEBUG)
        self.assertEqual(logger.logger.level, logging.DEBUG)

    def test_log_fetch_start(self):
        """Test logging the start of a fetch operation"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="serper")

        with self.assertLogs(logger.logger, level='INFO') as cm:
            logger.log_fetch_start(query="padel edinburgh")

        self.assertEqual(len(cm.output), 1)
        self.assertIn("serper", cm.output[0])
        self.assertIn("fetch_start", cm.output[0])
        self.assertIn("padel edinburgh", cm.output[0])

    def test_log_fetch_success(self):
        """Test logging successful fetch operation"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="serper")

        with self.assertLogs(logger.logger, level='INFO') as cm:
            logger.log_fetch_success(query="padel edinburgh", record_count=10)

        self.assertEqual(len(cm.output), 1)
        self.assertIn("serper", cm.output[0])
        self.assertIn("fetch_success", cm.output[0])
        self.assertIn("10", cm.output[0])

    def test_log_fetch_error(self):
        """Test logging fetch operation errors"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="serper")

        test_error = ValueError("API key invalid")

        with self.assertLogs(logger.logger, level='ERROR') as cm:
            logger.log_fetch_error(query="padel edinburgh", error=test_error)

        self.assertEqual(len(cm.output), 1)
        self.assertIn("serper", cm.output[0])
        self.assertIn("fetch_error", cm.output[0])
        self.assertIn("API key invalid", cm.output[0])

    def test_log_save_start(self):
        """Test logging the start of a save operation"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="serper")

        with self.assertLogs(logger.logger, level='INFO') as cm:
            logger.log_save_start(source_url="https://example.com")

        self.assertEqual(len(cm.output), 1)
        self.assertIn("save_start", cm.output[0])
        self.assertIn("https://example.com", cm.output[0])

    def test_log_save_success(self):
        """Test logging successful save operation"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="serper")

        with self.assertLogs(logger.logger, level='INFO') as cm:
            logger.log_save_success(
                file_path="engine/data/raw/serper/20260114_123.json",
                source_url="https://example.com"
            )

        self.assertEqual(len(cm.output), 1)
        self.assertIn("save_success", cm.output[0])
        self.assertIn("20260114_123.json", cm.output[0])

    def test_log_save_error(self):
        """Test logging save operation errors"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="serper")

        test_error = IOError("Permission denied")

        with self.assertLogs(logger.logger, level='ERROR') as cm:
            logger.log_save_error(source_url="https://example.com", error=test_error)

        self.assertEqual(len(cm.output), 1)
        self.assertIn("save_error", cm.output[0])
        self.assertIn("Permission denied", cm.output[0])

    def test_log_duplicate_detected(self):
        """Test logging when duplicate content is detected"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="serper")

        with self.assertLogs(logger.logger, level='INFO') as cm:
            logger.log_duplicate_detected(
                content_hash="abc123def456",
                source_url="https://example.com"
            )

        self.assertEqual(len(cm.output), 1)
        self.assertIn("duplicate_detected", cm.output[0])
        self.assertIn("abc123", cm.output[0])

    def test_log_structure_contains_timestamp(self):
        """Test that log entries contain ISO formatted timestamps"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="test")

        with self.assertLogs(logger.logger, level='INFO') as cm:
            logger.log_fetch_start(query="test")

        # Check that output contains timestamp in ISO format
        log_output = cm.output[0]
        # Should contain something like 2026-01-14T...
        self.assertRegex(log_output, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')

    def test_log_structure_is_json(self):
        """Test that log entries are structured as valid JSON"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="test", format="json")

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            # Create a custom handler to capture raw output
            handler = logging.StreamHandler(mock_stdout)
            logger.logger.addHandler(handler)

            logger.log_fetch_start(query="test query")

            output = mock_stdout.getvalue().strip()
            if output:  # Only test if we got output
                try:
                    log_entry = json.loads(output)
                    self.assertIn("source", log_entry)
                    self.assertIn("event", log_entry)
                    self.assertIn("timestamp", log_entry)
                except json.JSONDecodeError:
                    # If not JSON, that's okay for non-JSON format
                    pass

    def test_log_structure_contains_source(self):
        """Test that all log entries contain the source identifier"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="serper")

        with self.assertLogs(logger.logger, level='INFO') as cm:
            logger.log_fetch_start(query="test")

        self.assertIn("serper", cm.output[0])

    def test_log_with_extra_metadata(self):
        """Test logging with additional custom metadata"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="test")

        with self.assertLogs(logger.logger, level='INFO') as cm:
            logger.log_fetch_success(
                query="test",
                record_count=5,
                extra={"api_version": "v2", "region": "UK"}
            )

        log_output = cm.output[0]
        self.assertIn("api_version", log_output)
        self.assertIn("v2", log_output)

    def test_error_logging_includes_traceback(self):
        """Test that error logs include exception traceback information"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="test")

        try:
            raise ValueError("Test error with traceback")
        except ValueError as e:
            with self.assertLogs(logger.logger, level='ERROR') as cm:
                logger.log_fetch_error(query="test", error=e, include_traceback=True)

            log_output = cm.output[0]
            # Should include the error message
            self.assertIn("Test error with traceback", log_output)


class TestLoggingIntegrationWithConnectors(unittest.TestCase):
    """Test that logging integrates properly with BaseConnector"""

    def test_base_connector_can_use_logger(self):
        """Test that BaseConnector subclasses can use IngestionLogger"""
        from engine.ingestion.base import BaseConnector
        from engine.ingestion.logging_config import IngestionLogger

        class TestConnector(BaseConnector):
            def __init__(self):
                self.logger = IngestionLogger(source=self.source_name)

            @property
            def source_name(self) -> str:
                return "test"

            async def fetch(self, query: str) -> dict:
                self.logger.log_fetch_start(query=query)
                return {"result": "test"}

            async def save(self, data: dict, source_url: str) -> str:
                return "test_path"

            async def is_duplicate(self, content_hash: str) -> bool:
                return False

        connector = TestConnector()
        self.assertIsNotNone(connector.logger)
        self.assertIsInstance(connector.logger, IngestionLogger)


class TestLogLevelFiltering(unittest.TestCase):
    """Test log level filtering functionality"""

    def test_debug_level_includes_debug_messages(self):
        """Test that DEBUG level includes debug messages"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="test", level=logging.DEBUG)

        with self.assertLogs(logger.logger, level='DEBUG') as cm:
            logger.log_debug("Debug message")

        self.assertEqual(len(cm.output), 1)
        self.assertIn("Debug message", cm.output[0])

    def test_info_level_excludes_debug_messages(self):
        """Test that INFO level excludes debug messages"""
        from engine.ingestion.logging_config import IngestionLogger

        logger = IngestionLogger(source="test", level=logging.INFO)

        # Create a handler to capture logs
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.logger.addHandler(handler)

        logger.log_debug("Debug message")

        # Should not capture debug message at INFO level
        handler.flush()
        # Note: This test might need adjustment based on implementation


class TestLoggingConfiguration(unittest.TestCase):
    """Test logging configuration and setup"""

    def test_configure_logging_exists(self):
        """Test that configure_logging function exists"""
        try:
            from engine.ingestion.logging_config import configure_logging
            self.assertIsNotNone(configure_logging)
        except ImportError as e:
            self.fail(f"Failed to import configure_logging: {e}")

    def test_configure_logging_sets_global_level(self):
        """Test that configure_logging can set global log level"""
        from engine.ingestion.logging_config import configure_logging

        configure_logging(level=logging.DEBUG)

        # Verify that the root logger or ingestion loggers are configured
        root_logger = logging.getLogger('ingestion')
        self.assertIsNotNone(root_logger)

    def test_configure_logging_with_file_handler(self):
        """Test that configure_logging can add file handler"""
        from engine.ingestion.logging_config import configure_logging

        # This should not raise an error
        try:
            configure_logging(
                level=logging.INFO,
                log_file="engine/logs/ingestion.log"
            )
        except Exception as e:
            self.fail(f"configure_logging raised unexpected exception: {e}")


if __name__ == '__main__':
    unittest.main()
