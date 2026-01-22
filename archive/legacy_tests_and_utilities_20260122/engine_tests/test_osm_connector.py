"""
Tests for OpenStreetMap Overpass API Connector

This module tests the OSMConnector implementation which fetches sports facility
and venue data from the OpenStreetMap Overpass API.

The Overpass API allows querying OpenStreetMap data using Overpass QL:
- Query language for filtering OSM elements (nodes, ways, relations)
- Returns data in JSON or XML format
- Useful for finding sports facilities, amenities, and infrastructure

Test Coverage:
- Connector initialization and configuration
- API request formatting and execution (Overpass QL queries)
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


class TestOSMConnectorInitialization(unittest.IsolatedAsyncioTestCase):
    """Test OSMConnector initialization and basic properties"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        # Mock configuration
        self.mock_config = {
            "openstreetmap": {
                "enabled": True,
                "base_url": "https://overpass-api.de/api/interpreter",
                "timeout_seconds": 60,
                "rate_limits": {
                    "requests_per_minute": 10,
                    "requests_per_hour": 100
                },
                "default_params": {
                    "format": "json",
                    "radius": 50000,
                    "location": "55.9533,-3.1883"
                }
            }
        }

    async def test_osm_connector_can_be_imported(self):
        """Test that OSMConnector class can be imported"""
        try:
            from engine.ingestion.connectors.open_street_map import OSMConnector
            self.assertIsNotNone(OSMConnector)
        except ImportError:
            self.fail("Failed to import OSMConnector - implementation not yet created")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_osm_connector_can_be_instantiated(self, mock_file, mock_yaml):
        """Test that OSMConnector can be instantiated with valid config"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config

        connector = OSMConnector()
        self.assertIsNotNone(connector)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_osm_connector_has_correct_source_name(self, mock_file, mock_yaml):
        """Test that OSMConnector provides source_name as 'openstreetmap'"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config

        connector = OSMConnector()
        self.assertEqual(connector.source_name, "openstreetmap")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_osm_connector_loads_config(self, mock_file, mock_yaml):
        """Test that OSMConnector loads configuration from sources.yaml"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config

        connector = OSMConnector()

        # Verify configuration was loaded
        self.assertEqual(connector.base_url, "https://overpass-api.de/api/interpreter")
        self.assertEqual(connector.timeout_seconds, 60)

    async def test_osm_connector_raises_error_without_config(self):
        """Test that OSMConnector raises error if config file missing"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        with patch('builtins.open', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                OSMConnector()

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_osm_connector_raises_error_without_base_url(self, mock_file, mock_yaml):
        """Test that OSMConnector raises error if base URL not configured"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        # Config without base URL
        invalid_config = {
            "openstreetmap": {
                "enabled": True,
                "base_url": None
            }
        }
        mock_yaml.return_value = invalid_config

        with self.assertRaises(ValueError) as context:
            OSMConnector()

        # Check error message mentions base URL or configuration
        error_msg = str(context.exception).lower()
        self.assertTrue("url" in error_msg or "configured" in error_msg)


class TestOSMConnectorFetch(unittest.IsolatedAsyncioTestCase):
    """Test OSMConnector fetch method - API request logic"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "openstreetmap": {
                "enabled": True,
                "base_url": "https://overpass-api.de/api/interpreter",
                "timeout_seconds": 60,
                "default_params": {
                    "format": "json",
                    "radius": 50000,
                    "location": "55.9533,-3.1883"
                }
            }
        }

        # Mock Overpass API response
        self.mock_osm_response = {
            "version": 0.6,
            "generator": "Overpass API",
            "elements": [
                {
                    "type": "node",
                    "id": 123456789,
                    "lat": 55.9533,
                    "lon": -3.1883,
                    "tags": {
                        "name": "Edinburgh Padel Club",
                        "sport": "padel",
                        "leisure": "sports_centre",
                        "addr:city": "Edinburgh",
                        "addr:postcode": "EH1 1AA"
                    }
                },
                {
                    "type": "way",
                    "id": 987654321,
                    "nodes": [1, 2, 3, 4, 1],
                    "tags": {
                        "name": "Padel Courts",
                        "sport": "padel",
                        "leisure": "pitch"
                    }
                }
            ]
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_makes_api_request(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch method makes HTTP POST request to Overpass API"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config

        # Mock aiohttp session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_osm_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = OSMConnector()
        result = await connector.fetch("padel")

        # Verify API was called with POST
        mock_session.post.assert_called_once()
        self.assertEqual(result, self.mock_osm_response)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_builds_overpass_ql_query(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch builds proper Overpass QL query"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_osm_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = OSMConnector()
        await connector.fetch("padel")

        # Verify Overpass QL query was sent in request
        call_kwargs = mock_session.post.call_args.kwargs
        self.assertIn('data', call_kwargs)
        query_data = call_kwargs['data']

        # Check that query contains essential Overpass QL elements
        self.assertIn('[out:json]', query_data)
        self.assertIn('padel', query_data)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_spatial_filter(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes spatial filter (around) in query"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_osm_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = OSMConnector()
        await connector.fetch("padel")

        # Verify spatial filter is in query
        call_kwargs = mock_session.post.call_args.kwargs
        query_data = call_kwargs['data']

        # Should include (around:radius,lat,lon) filter
        self.assertIn('around', query_data)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_http_error(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch raises error on HTTP failure"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config

        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 429  # Too Many Requests
        mock_response.text = AsyncMock(return_value="Rate limit exceeded")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = OSMConnector()

        with self.assertRaises(Exception):
            await connector.fetch("padel")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_network_timeout(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch handles network timeout gracefully"""
        from engine.ingestion.connectors.open_street_map import OSMConnector
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

        connector = OSMConnector()

        with self.assertRaises(asyncio.TimeoutError):
            await connector.fetch("padel")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_empty_results(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch handles empty results (no matching facilities)"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config

        # Mock empty response
        empty_response = {
            "version": 0.6,
            "generator": "Overpass API",
            "elements": []
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

        connector = OSMConnector()
        result = await connector.fetch("padel")

        # Should return the response even with empty results
        self.assertEqual(result, empty_response)
        self.assertEqual(len(result['elements']), 0)


class TestOSMConnectorSave(unittest.IsolatedAsyncioTestCase):
    """Test OSMConnector save method - data persistence"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "openstreetmap": {
                "enabled": True,
                "base_url": "https://overpass-api.de/api/interpreter"
            }
        }

        self.test_data = {
            "version": 0.6,
            "generator": "Overpass API",
            "elements": [
                {
                    "type": "node",
                    "id": 123456789,
                    "lat": 55.9533,
                    "lon": -3.1883,
                    "tags": {"name": "Edinburgh Padel Club", "sport": "padel"}
                }
            ]
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_street_map.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_file(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method creates JSON file"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = OSMConnector()
        connector.db = mock_db

        file_path = await connector.save(
            self.test_data,
            "https://overpass-api.de/api/interpreter?query=padel"
        )

        # Verify save_json was called
        mock_save_json.assert_called_once()
        self.assertIsInstance(file_path, str)
        self.assertIn("engine/data/raw/openstreetmap/", file_path)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_street_map.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_database_record(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method creates RawIngestion database record"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = OSMConnector()
        connector.db = mock_db

        await connector.save(
            self.test_data,
            "https://overpass-api.de/api/interpreter?query=padel"
        )

        # Verify database record was created
        mock_db.rawingestion.create.assert_called_once()
        call_args = mock_db.rawingestion.create.call_args

        # Check that required fields are present
        data_arg = call_args.kwargs['data']
        self.assertEqual(data_arg['source'], 'openstreetmap')
        self.assertEqual(data_arg['source_url'], 'https://overpass-api.de/api/interpreter?query=padel')
        self.assertIn('file_path', data_arg)
        self.assertIn('hash', data_arg)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_street_map.save_json')
    @patch('prisma.Prisma')
    async def test_save_returns_file_path(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method returns the file path"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config

        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = OSMConnector()
        connector.db = mock_db

        file_path = await connector.save(
            self.test_data,
            "https://overpass-api.de/api/interpreter?query=padel"
        )

        self.assertIsInstance(file_path, str)
        self.assertIn(".json", file_path)
        self.assertIn("openstreetmap", file_path)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_street_map.save_json')
    @patch('prisma.Prisma')
    async def test_save_includes_element_count_in_metadata(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save includes element count in metadata_json"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config

        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = OSMConnector()
        connector.db = mock_db

        await connector.save(
            self.test_data,
            "https://overpass-api.de/api/interpreter?query=padel"
        )

        # Verify metadata includes element count
        call_args = mock_db.rawingestion.create.call_args
        data_arg = call_args.kwargs['data']

        # metadata_json should include element count
        metadata = json.loads(data_arg['metadata_json'])
        self.assertIn('element_count', metadata)
        self.assertEqual(metadata['element_count'], 1)


class TestOSMConnectorDeduplication(unittest.IsolatedAsyncioTestCase):
    """Test OSMConnector deduplication logic"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "openstreetmap": {
                "enabled": True,
                "base_url": "https://overpass-api.de/api/interpreter"
            }
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_street_map.check_duplicate')
    async def test_is_duplicate_checks_database(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate queries the database"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False

        connector = OSMConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("test_hash_123")

        # Verify check_duplicate was called
        mock_check_dup.assert_called_once_with(connector.db, "test_hash_123")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_street_map.check_duplicate')
    async def test_is_duplicate_returns_true_for_existing(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate returns True for existing content"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = True

        connector = OSMConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("existing_hash")

        self.assertTrue(result)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_street_map.check_duplicate')
    async def test_is_duplicate_returns_false_for_new(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate returns False for new content"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False

        connector = OSMConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("new_hash")

        self.assertFalse(result)


class TestOSMConnectorIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for complete fetch-save-deduplicate workflow"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "openstreetmap": {
                "enabled": True,
                "base_url": "https://overpass-api.de/api/interpreter",
                "default_params": {
                    "format": "json",
                    "radius": 50000,
                    "location": "55.9533,-3.1883"
                }
            }
        }

        self.mock_response = {
            "version": 0.6,
            "generator": "Overpass API",
            "elements": [
                {
                    "type": "node",
                    "id": 123456789,
                    "lat": 55.9533,
                    "lon": -3.1883,
                    "tags": {"name": "Edinburgh Padel Club", "sport": "padel"}
                }
            ]
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    @patch('engine.ingestion.connectors.open_street_map.save_json')
    @patch('engine.ingestion.connectors.open_street_map.check_duplicate')
    async def test_complete_workflow_fetch_and_save(
        self, mock_check_dup, mock_save_json, mock_session_class, mock_file, mock_yaml
    ):
        """Test complete workflow: fetch data, check duplicate, save"""
        from engine.ingestion.connectors.open_street_map import OSMConnector

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

        connector = OSMConnector()
        connector.db = mock_db

        # Execute workflow
        data = await connector.fetch("padel")
        self.assertEqual(data, self.mock_response)

        file_path = await connector.save(
            data,
            "https://overpass-api.de/api/interpreter?query=padel"
        )
        self.assertIn("openstreetmap", file_path)


if __name__ == "__main__":
    unittest.main()
