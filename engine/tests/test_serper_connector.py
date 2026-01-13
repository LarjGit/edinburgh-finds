"""
Tests for Serper API Connector

This module tests the SerperConnector implementation which fetches search
results from the Serper API (Google search results API).

Test Coverage:
- Connector initialization and configuration
- API request formatting and execution
- Response parsing and validation
- Data persistence to filesystem and database
- Deduplication logic
- Error handling (network, API, validation errors)
- Rate limiting compliance
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime
import json
import os


class TestSerperConnectorInitialization(unittest.IsolatedAsyncioTestCase):
    """Test SerperConnector initialization and basic properties"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        # Mock configuration
        self.mock_config = {
            "serper": {
                "enabled": True,
                "api_key": "test_api_key_123",
                "base_url": "https://google.serper.dev",
                "timeout_seconds": 30,
                "rate_limits": {
                    "requests_per_minute": 60,
                    "requests_per_hour": 1000
                },
                "default_params": {
                    "gl": "uk",
                    "hl": "en",
                    "num": 10
                }
            }
        }

    async def test_serper_connector_can_be_imported(self):
        """Test that SerperConnector class can be imported"""
        try:
            from engine.ingestion.serper import SerperConnector
            self.assertIsNotNone(SerperConnector)
        except ImportError:
            self.fail("Failed to import SerperConnector - implementation not yet created")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_serper_connector_can_be_instantiated(self, mock_file, mock_yaml):
        """Test that SerperConnector can be instantiated with valid config"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config

        connector = SerperConnector()
        self.assertIsNotNone(connector)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_serper_connector_has_correct_source_name(self, mock_file, mock_yaml):
        """Test that SerperConnector provides source_name as 'serper'"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config

        connector = SerperConnector()
        self.assertEqual(connector.source_name, "serper")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_serper_connector_loads_config(self, mock_file, mock_yaml):
        """Test that SerperConnector loads configuration from sources.yaml"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config

        connector = SerperConnector()

        # Verify configuration was loaded
        self.assertEqual(connector.api_key, "test_api_key_123")
        self.assertEqual(connector.base_url, "https://google.serper.dev")

    async def test_serper_connector_raises_error_without_config(self):
        """Test that SerperConnector raises error if config file missing"""
        from engine.ingestion.serper import SerperConnector

        with patch('builtins.open', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                SerperConnector()

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_serper_connector_raises_error_without_api_key(self, mock_file, mock_yaml):
        """Test that SerperConnector raises error if API key not configured"""
        from engine.ingestion.serper import SerperConnector

        # Config without API key
        invalid_config = {
            "serper": {
                "enabled": True,
                "api_key": None,
                "base_url": "https://google.serper.dev"
            }
        }
        mock_yaml.return_value = invalid_config

        with self.assertRaises(ValueError) as context:
            SerperConnector()

        # Check error message mentions API key configuration
        error_msg = str(context.exception).lower()
        self.assertTrue("api" in error_msg or "key" in error_msg or "configured" in error_msg)


class TestSerperConnectorFetch(unittest.IsolatedAsyncioTestCase):
    """Test SerperConnector fetch method - API request logic"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "serper": {
                "enabled": True,
                "api_key": "test_api_key_123",
                "base_url": "https://google.serper.dev",
                "timeout_seconds": 30,
                "default_params": {
                    "gl": "uk",
                    "hl": "en",
                    "num": 10
                }
            }
        }

        self.mock_serper_response = {
            "searchParameters": {
                "q": "padel edinburgh",
                "gl": "uk",
                "hl": "en",
                "num": 10,
                "type": "search"
            },
            "organic": [
                {
                    "title": "Edinburgh Padel Club",
                    "link": "https://example.com/edinburgh-padel",
                    "snippet": "Premier padel courts in Edinburgh",
                    "position": 1
                },
                {
                    "title": "Padel Courts Near You",
                    "link": "https://example.com/padel-courts",
                    "snippet": "Find padel courts in Edinburgh area",
                    "position": 2
                }
            ],
            "credits": 1
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_makes_api_request(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch method makes HTTP request to Serper API"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config

        # Mock aiohttp session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_serper_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = SerperConnector()
        result = await connector.fetch("padel edinburgh")

        # Verify API was called
        mock_session.post.assert_called_once()
        self.assertEqual(result, self.mock_serper_response)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_api_key_header(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes API key in request headers"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_serper_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = SerperConnector()
        await connector.fetch("padel edinburgh")

        # Verify API key was included in headers
        call_kwargs = mock_session.post.call_args.kwargs
        self.assertIn('headers', call_kwargs)
        self.assertIn('X-API-KEY', call_kwargs['headers'])
        self.assertEqual(call_kwargs['headers']['X-API-KEY'], "test_api_key_123")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_default_params(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes default parameters from config"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_serper_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = SerperConnector()
        await connector.fetch("padel edinburgh")

        # Verify default params were included in request body
        call_kwargs = mock_session.post.call_args.kwargs
        self.assertIn('json', call_kwargs)
        request_body = call_kwargs['json']
        self.assertEqual(request_body['gl'], "uk")
        self.assertEqual(request_body['hl'], "en")
        self.assertEqual(request_body['num'], 10)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_http_error(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch raises error on HTTP failure"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config

        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = SerperConnector()

        with self.assertRaises(Exception):
            await connector.fetch("padel edinburgh")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_network_timeout(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch handles network timeout gracefully"""
        from engine.ingestion.serper import SerperConnector
        import asyncio

        mock_yaml.return_value = self.mock_config

        # Mock timeout error - needs to raise when used as context manager
        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = SerperConnector()

        with self.assertRaises(asyncio.TimeoutError):
            await connector.fetch("padel edinburgh")


class TestSerperConnectorSave(unittest.IsolatedAsyncioTestCase):
    """Test SerperConnector save method - data persistence"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "serper": {
                "enabled": True,
                "api_key": "test_api_key_123",
                "base_url": "https://google.serper.dev"
            }
        }

        self.test_data = {
            "searchParameters": {"q": "padel edinburgh"},
            "organic": [{"title": "Test", "link": "https://example.com"}]
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.serper.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_file(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method creates JSON file"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = SerperConnector()
        connector.db = mock_db

        file_path = await connector.save(self.test_data, "https://google.serper.dev/search")

        # Verify save_json was called
        mock_save_json.assert_called_once()
        self.assertIsInstance(file_path, str)
        self.assertIn("engine/data/raw/serper/", file_path)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.serper.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_database_record(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method creates RawIngestion database record"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = SerperConnector()
        connector.db = mock_db

        await connector.save(self.test_data, "https://google.serper.dev/search")

        # Verify database record was created
        mock_db.rawingestion.create.assert_called_once()
        call_args = mock_db.rawingestion.create.call_args

        # Check that required fields are present
        data_arg = call_args.kwargs['data']
        self.assertEqual(data_arg['source'], 'serper')
        self.assertEqual(data_arg['source_url'], 'https://google.serper.dev/search')
        self.assertIn('file_path', data_arg)
        self.assertIn('hash', data_arg)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.serper.save_json')
    @patch('prisma.Prisma')
    async def test_save_returns_file_path(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method returns the file path"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config

        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = SerperConnector()
        connector.db = mock_db

        file_path = await connector.save(self.test_data, "https://google.serper.dev/search")

        self.assertIsInstance(file_path, str)
        self.assertIn(".json", file_path)
        self.assertIn("serper", file_path)


class TestSerperConnectorDeduplication(unittest.IsolatedAsyncioTestCase):
    """Test SerperConnector deduplication logic"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "serper": {
                "enabled": True,
                "api_key": "test_api_key_123",
                "base_url": "https://google.serper.dev"
            }
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.serper.check_duplicate')
    async def test_is_duplicate_checks_database(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate queries the database"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False

        connector = SerperConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("test_hash_123")

        # Verify check_duplicate was called
        mock_check_dup.assert_called_once_with(connector.db, "test_hash_123")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.serper.check_duplicate')
    async def test_is_duplicate_returns_true_for_existing(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate returns True for existing content"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = True

        connector = SerperConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("existing_hash")

        self.assertTrue(result)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.serper.check_duplicate')
    async def test_is_duplicate_returns_false_for_new(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate returns False for new content"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False

        connector = SerperConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("new_hash")

        self.assertFalse(result)


class TestSerperConnectorIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for complete fetch-save-deduplicate workflow"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "serper": {
                "enabled": True,
                "api_key": "test_api_key_123",
                "base_url": "https://google.serper.dev",
                "default_params": {
                    "gl": "uk",
                    "hl": "en",
                    "num": 10
                }
            }
        }

        self.mock_response = {
            "searchParameters": {"q": "padel edinburgh"},
            "organic": [{"title": "Test", "link": "https://example.com"}]
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    @patch('engine.ingestion.serper.save_json')
    @patch('engine.ingestion.serper.check_duplicate')
    async def test_complete_workflow_fetch_and_save(
        self, mock_check_dup, mock_save_json, mock_session_class, mock_file, mock_yaml
    ):
        """Test complete workflow: fetch data, check duplicate, save"""
        from engine.ingestion.serper import SerperConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False  # Not a duplicate

        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})

        connector = SerperConnector()
        connector.db = mock_db

        # Execute workflow
        data = await connector.fetch("padel edinburgh")
        self.assertEqual(data, self.mock_response)

        file_path = await connector.save(data, "https://google.serper.dev/search")
        self.assertIn("serper", file_path)


if __name__ == "__main__":
    unittest.main()
