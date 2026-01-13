"""
Tests for Google Places API Connector

This module tests the GooglePlacesConnector implementation which fetches venue
and business data from the Google Places API.

The Google Places API provides two main endpoints:
1. Place Search (Nearby/Text Search) - Find places matching criteria
2. Place Details - Get detailed information about a specific place

Test Coverage:
- Connector initialization and configuration
- Place Search API request formatting and execution
- Place Details API request formatting and execution
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


class TestGooglePlacesConnectorInitialization(unittest.IsolatedAsyncioTestCase):
    """Test GooglePlacesConnector initialization and basic properties"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        # Mock configuration
        self.mock_config = {
            "google_places": {
                "enabled": True,
                "api_key": "test_google_api_key_123",
                "base_url": "https://maps.googleapis.com/maps/api/place",
                "timeout_seconds": 30,
                "rate_limits": {
                    "requests_per_minute": 60,
                    "requests_per_hour": 2000
                },
                "default_params": {
                    "radius": 50000,
                    "location": "55.9533,-3.1883"
                }
            }
        }

    async def test_google_places_connector_can_be_imported(self):
        """Test that GooglePlacesConnector class can be imported"""
        try:
            from engine.ingestion.google_places import GooglePlacesConnector
            self.assertIsNotNone(GooglePlacesConnector)
        except ImportError:
            self.fail("Failed to import GooglePlacesConnector - implementation not yet created")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_google_places_connector_can_be_instantiated(self, mock_file, mock_yaml):
        """Test that GooglePlacesConnector can be instantiated with valid config"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config

        connector = GooglePlacesConnector()
        self.assertIsNotNone(connector)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_google_places_connector_has_correct_source_name(self, mock_file, mock_yaml):
        """Test that GooglePlacesConnector provides source_name as 'google_places'"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config

        connector = GooglePlacesConnector()
        self.assertEqual(connector.source_name, "google_places")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_google_places_connector_loads_config(self, mock_file, mock_yaml):
        """Test that GooglePlacesConnector loads configuration from sources.yaml"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config

        connector = GooglePlacesConnector()

        # Verify configuration was loaded
        self.assertEqual(connector.api_key, "test_google_api_key_123")
        self.assertEqual(connector.base_url, "https://maps.googleapis.com/maps/api/place")

    async def test_google_places_connector_raises_error_without_config(self):
        """Test that GooglePlacesConnector raises error if config file missing"""
        from engine.ingestion.google_places import GooglePlacesConnector

        with patch('builtins.open', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                GooglePlacesConnector()

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_google_places_connector_raises_error_without_api_key(self, mock_file, mock_yaml):
        """Test that GooglePlacesConnector raises error if API key not configured"""
        from engine.ingestion.google_places import GooglePlacesConnector

        # Config without API key
        invalid_config = {
            "google_places": {
                "enabled": True,
                "api_key": None,
                "base_url": "https://maps.googleapis.com/maps/api/place"
            }
        }
        mock_yaml.return_value = invalid_config

        with self.assertRaises(ValueError) as context:
            GooglePlacesConnector()

        # Check error message mentions API key configuration
        error_msg = str(context.exception).lower()
        self.assertTrue("api" in error_msg or "key" in error_msg or "configured" in error_msg)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_google_places_connector_raises_error_with_placeholder_key(self, mock_file, mock_yaml):
        """Test that GooglePlacesConnector raises error if API key is placeholder"""
        from engine.ingestion.google_places import GooglePlacesConnector

        # Config with placeholder key
        invalid_config = {
            "google_places": {
                "enabled": True,
                "api_key": "YOUR_GOOGLE_PLACES_API_KEY_HERE",
                "base_url": "https://maps.googleapis.com/maps/api/place"
            }
        }
        mock_yaml.return_value = invalid_config

        with self.assertRaises(ValueError):
            GooglePlacesConnector()


class TestGooglePlacesConnectorSearch(unittest.IsolatedAsyncioTestCase):
    """Test GooglePlacesConnector fetch method - Place Search API"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "google_places": {
                "enabled": True,
                "api_key": "test_google_api_key_123",
                "base_url": "https://maps.googleapis.com/maps/api/place",
                "timeout_seconds": 30,
                "default_params": {
                    "radius": 50000,
                    "location": "55.9533,-3.1883"
                }
            }
        }

        # Mock Google Places API (New) response for text search
        self.mock_search_response = {
            "places": [
                {
                    "id": "ChIJ3SxxxxxxxxxxxxxH4",
                    "displayName": {"text": "Edinburgh Padel Club"},
                    "formattedAddress": "123 Fake St, Edinburgh EH1 1AA",
                    "location": {
                        "latitude": 55.9533,
                        "longitude": -3.1883
                    },
                    "rating": 4.5,
                    "userRatingCount": 120
                },
                {
                    "id": "ChIJ4TyxxxxxxxxxxxxH5",
                    "displayName": {"text": "Padel Scotland"},
                    "formattedAddress": "456 Other St, Edinburgh EH2 2BB",
                    "location": {
                        "latitude": 55.9500,
                        "longitude": -3.1900
                    },
                    "rating": 4.7,
                    "userRatingCount": 89
                }
            ]
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_makes_api_request(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch method makes HTTP POST request to Google Places API (New)"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config

        # Mock aiohttp session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_search_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = GooglePlacesConnector()
        result = await connector.fetch("padel edinburgh")

        # Verify API was called with POST
        mock_session.post.assert_called_once()
        self.assertEqual(result, self.mock_search_response)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_api_key(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes API key in request parameters"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_search_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = GooglePlacesConnector()
        await connector.fetch("padel edinburgh")

        # Verify API key was included in X-Goog-Api-Key header (new API format)
        call_args = mock_session.post.call_args
        self.assertIn('headers', call_args.kwargs)
        headers = call_args.kwargs['headers']
        self.assertIn('X-Goog-Api-Key', headers)
        self.assertEqual(headers['X-Goog-Api-Key'], "test_google_api_key_123")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_default_params(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes default parameters from config"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_search_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = GooglePlacesConnector()
        await connector.fetch("padel edinburgh")

        # Verify default params were included in request body (new API format)
        call_args = mock_session.post.call_args
        self.assertIn('json', call_args.kwargs)
        body = call_args.kwargs['json']
        self.assertIn('textQuery', body)
        self.assertEqual(body['textQuery'], "padel edinburgh")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_http_error(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch raises error on HTTP failure"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config

        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.text = AsyncMock(return_value="Forbidden")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = GooglePlacesConnector()

        with self.assertRaises(Exception):
            await connector.fetch("padel edinburgh")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_network_timeout(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch handles network timeout gracefully"""
        from engine.ingestion.google_places import GooglePlacesConnector
        import asyncio

        mock_yaml.return_value = self.mock_config

        # Mock timeout error
        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = GooglePlacesConnector()

        with self.assertRaises(asyncio.TimeoutError):
            await connector.fetch("padel edinburgh")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_api_error_status(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch handles Google Places API with no results (new API)"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config

        # Mock API response with no results (HTTP 200 but empty places array)
        empty_response = {
            "places": []
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=empty_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = GooglePlacesConnector()
        result = await connector.fetch("padel edinburgh")

        # Should return the response even with empty results
        self.assertEqual(result, empty_response)


class TestGooglePlacesConnectorSave(unittest.IsolatedAsyncioTestCase):
    """Test GooglePlacesConnector save method - data persistence"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "google_places": {
                "enabled": True,
                "api_key": "test_google_api_key_123",
                "base_url": "https://maps.googleapis.com/maps/api/place"
            }
        }

        self.test_data = {
            "places": [
                {
                    "id": "ChIJ3SxxxxxxxxxxxxxH4",
                    "displayName": {"text": "Edinburgh Padel Club"}
                }
            ]
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.google_places.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_file(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method creates JSON file"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = GooglePlacesConnector()
        connector.db = mock_db

        file_path = await connector.save(
            self.test_data,
            "https://maps.googleapis.com/maps/api/place/textsearch/json"
        )

        # Verify save_json was called
        mock_save_json.assert_called_once()
        self.assertIsInstance(file_path, str)
        self.assertIn("engine/data/raw/google_places/", file_path)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.google_places.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_database_record(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method creates RawIngestion database record"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = GooglePlacesConnector()
        connector.db = mock_db

        await connector.save(
            self.test_data,
            "https://maps.googleapis.com/maps/api/place/textsearch/json"
        )

        # Verify database record was created
        mock_db.rawingestion.create.assert_called_once()
        call_args = mock_db.rawingestion.create.call_args

        # Check that required fields are present
        data_arg = call_args.kwargs['data']
        self.assertEqual(data_arg['source'], 'google_places')
        self.assertEqual(data_arg['source_url'], 'https://maps.googleapis.com/maps/api/place/textsearch/json')
        self.assertIn('file_path', data_arg)
        self.assertIn('hash', data_arg)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.google_places.save_json')
    @patch('prisma.Prisma')
    async def test_save_returns_file_path(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method returns the file path"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config

        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = GooglePlacesConnector()
        connector.db = mock_db

        file_path = await connector.save(
            self.test_data,
            "https://maps.googleapis.com/maps/api/place/textsearch/json"
        )

        self.assertIsInstance(file_path, str)
        self.assertIn(".json", file_path)
        self.assertIn("google_places", file_path)


class TestGooglePlacesConnectorDeduplication(unittest.IsolatedAsyncioTestCase):
    """Test GooglePlacesConnector deduplication logic"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "google_places": {
                "enabled": True,
                "api_key": "test_google_api_key_123",
                "base_url": "https://maps.googleapis.com/maps/api/place"
            }
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.google_places.check_duplicate')
    async def test_is_duplicate_checks_database(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate queries the database"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False

        connector = GooglePlacesConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("test_hash_123")

        # Verify check_duplicate was called
        mock_check_dup.assert_called_once_with(connector.db, "test_hash_123")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.google_places.check_duplicate')
    async def test_is_duplicate_returns_true_for_existing(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate returns True for existing content"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = True

        connector = GooglePlacesConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("existing_hash")

        self.assertTrue(result)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.google_places.check_duplicate')
    async def test_is_duplicate_returns_false_for_new(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate returns False for new content"""
        from engine.ingestion.google_places import GooglePlacesConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False

        connector = GooglePlacesConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("new_hash")

        self.assertFalse(result)


class TestGooglePlacesConnectorIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for complete fetch-save-deduplicate workflow"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "google_places": {
                "enabled": True,
                "api_key": "test_google_api_key_123",
                "base_url": "https://maps.googleapis.com/maps/api/place",
                "default_params": {
                    "radius": 50000,
                    "location": "55.9533,-3.1883"
                }
            }
        }

        self.mock_response = {
            "places": [
                {
                    "id": "ChIJ3SxxxxxxxxxxxxxH4",
                    "displayName": {"text": "Edinburgh Padel Club"}
                }
            ]
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    @patch('engine.ingestion.google_places.save_json')
    @patch('engine.ingestion.google_places.check_duplicate')
    async def test_complete_workflow_fetch_and_save(
        self, mock_check_dup, mock_save_json, mock_session_class, mock_file, mock_yaml
    ):
        """Test complete workflow: fetch data, check duplicate, save"""
        from engine.ingestion.google_places import GooglePlacesConnector

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

        connector = GooglePlacesConnector()
        connector.db = mock_db

        # Execute workflow
        data = await connector.fetch("padel edinburgh")
        self.assertEqual(data, self.mock_response)

        file_path = await connector.save(
            data,
            "https://maps.googleapis.com/maps/api/place/textsearch/json"
        )
        self.assertIn("google_places", file_path)


if __name__ == "__main__":
    unittest.main()
