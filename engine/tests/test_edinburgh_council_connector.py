"""
Tests for Edinburgh Council ArcGIS Connector

This module tests the EdinburghCouncilConnector implementation which fetches
civic and facility data from the City of Edinburgh Council's Open Spatial
Data Portal powered by ArcGIS Hub.

The Edinburgh Council portal provides data including:
- Community facilities (sports centers, libraries, community centers)
- Parks and green spaces
- Education facilities (schools, nurseries)
- Planning and property data
- Transportation infrastructure

Test Coverage:
- Connector initialization and configuration
- ArcGIS REST API request formatting and execution
- Query parameter handling (where clause, spatial filters)
- GeoJSON response parsing and validation
- Data persistence to filesystem and database
- Deduplication logic
- Error handling (network, API, validation errors)
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime
import json
import os


class TestEdinburghCouncilConnectorInitialization(unittest.IsolatedAsyncioTestCase):
    """Test EdinburghCouncilConnector initialization and basic properties"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        # Mock configuration
        self.mock_config = {
            "edinburgh_council": {
                "enabled": True,
                "api_key": None,  # Public data - no API key required
                "base_url": "https://data.edinburghcouncilmaps.info/datasets",
                "timeout_seconds": 30,
                "default_params": {
                    "outFields": "*",
                    "f": "geojson",
                    "returnGeometry": "true"
                }
            }
        }

    async def test_edinburgh_council_connector_can_be_imported(self):
        """Test that EdinburghCouncilConnector class can be imported"""
        try:
            from engine.ingestion.edinburgh_council import EdinburghCouncilConnector
            self.assertIsNotNone(EdinburghCouncilConnector)
        except ImportError:
            self.fail("Failed to import EdinburghCouncilConnector - implementation not yet created")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_edinburgh_council_connector_can_be_instantiated(self, mock_file, mock_yaml):
        """Test that EdinburghCouncilConnector can be instantiated with valid config"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        connector = EdinburghCouncilConnector()
        self.assertIsNotNone(connector)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_edinburgh_council_connector_has_correct_source_name(self, mock_file, mock_yaml):
        """Test that EdinburghCouncilConnector provides source_name as 'edinburgh_council'"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        connector = EdinburghCouncilConnector()
        self.assertEqual(connector.source_name, "edinburgh_council")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_edinburgh_council_connector_loads_config(self, mock_file, mock_yaml):
        """Test that EdinburghCouncilConnector loads configuration from sources.yaml"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        connector = EdinburghCouncilConnector()

        # Verify configuration was loaded
        self.assertEqual(connector.base_url, "https://data.edinburghcouncilmaps.info/datasets")
        self.assertEqual(connector.timeout, 30)

    async def test_edinburgh_council_connector_raises_error_without_config(self):
        """Test that EdinburghCouncilConnector raises error if config file missing"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        with patch('builtins.open', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                EdinburghCouncilConnector()

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_edinburgh_council_connector_works_without_api_key(self, mock_file, mock_yaml):
        """Test that EdinburghCouncilConnector works with null API key (public data)"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        connector = EdinburghCouncilConnector()
        self.assertIsNone(connector.api_key)  # Public data doesn't require key


class TestEdinburghCouncilConnectorFetch(unittest.IsolatedAsyncioTestCase):
    """Test EdinburghCouncilConnector fetch method - ArcGIS REST API requests"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "edinburgh_council": {
                "enabled": True,
                "api_key": None,
                "base_url": "https://data.edinburghcouncilmaps.info/datasets",
                "timeout_seconds": 30,
                "default_params": {
                    "outFields": "*",
                    "f": "geojson",
                    "returnGeometry": "true"
                }
            }
        }

        # Mock ArcGIS REST API GeoJSON response
        self.mock_arcgis_response = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": 1,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.1883, 55.9533]
                    },
                    "properties": {
                        "OBJECTID": 1,
                        "name": "Edinburgh Leisure Centre",
                        "address": "123 Main Street",
                        "postcode": "EH1 1AA",
                        "facility_type": "Sports Centre",
                        "ward": "City Centre"
                    }
                },
                {
                    "type": "Feature",
                    "id": 2,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.2034, 55.9426]
                    },
                    "properties": {
                        "OBJECTID": 2,
                        "name": "Portobello Community Centre",
                        "address": "456 High Street",
                        "postcode": "EH15 2BB",
                        "facility_type": "Community Centre",
                        "ward": "Portobello/Craigmillar"
                    }
                }
            ]
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_makes_api_request(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch method makes HTTP GET request to ArcGIS REST endpoint"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        # Mock aiohttp session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_arcgis_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = EdinburghCouncilConnector()
        result = await connector.fetch("sports_facilities")

        # Verify API was called with GET
        mock_session.get.assert_called_once()
        self.assertEqual(result, self.mock_arcgis_response)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_query_parameters(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes ArcGIS query parameters"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_arcgis_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = EdinburghCouncilConnector()
        await connector.fetch("sports_facilities")

        # Verify query parameters were included
        call_args = mock_session.get.call_args
        self.assertIn('params', call_args.kwargs)
        params = call_args.kwargs['params']

        self.assertEqual(params['outFields'], '*')
        self.assertEqual(params['f'], 'geojson')
        self.assertEqual(params['returnGeometry'], 'true')

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_where_clause(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes where clause for filtering"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_arcgis_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = EdinburghCouncilConnector()
        await connector.fetch("sports_facilities")

        # Verify where clause was included (defaults to 1=1 for all records)
        call_args = mock_session.get.call_args
        params = call_args.kwargs['params']
        self.assertIn('where', params)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_builds_correct_url(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch builds correct ArcGIS Feature Service URL"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_arcgis_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = EdinburghCouncilConnector()
        await connector.fetch("sports_facilities")

        # Verify URL includes dataset ID and /query endpoint
        call_args = mock_session.get.call_args
        url = call_args.args[0]
        self.assertIn('sports_facilities', url)
        self.assertIn('/query', url)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_http_error(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch raises error on HTTP failure"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = EdinburghCouncilConnector()

        with self.assertRaises(Exception):
            await connector.fetch("sports_facilities")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_network_timeout(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch handles network timeout gracefully"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector
        import asyncio

        mock_yaml.return_value = self.mock_config

        # Mock timeout error
        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = EdinburghCouncilConnector()

        with self.assertRaises(asyncio.TimeoutError):
            await connector.fetch("sports_facilities")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_empty_feature_collection(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch handles response with no features"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        # Mock API response with no features
        empty_response = {
            "type": "FeatureCollection",
            "features": []
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=empty_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = EdinburghCouncilConnector()
        result = await connector.fetch("sports_facilities")

        # Should return the response even with empty features
        self.assertEqual(result, empty_response)
        self.assertEqual(len(result['features']), 0)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_fetch_raises_error_on_invalid_dataset_id(self, mock_file, mock_yaml):
        """Test that fetch validates dataset ID"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        connector = EdinburghCouncilConnector()

        # Test with empty dataset ID
        with self.assertRaises(ValueError):
            await connector.fetch("")


class TestEdinburghCouncilConnectorSave(unittest.IsolatedAsyncioTestCase):
    """Test EdinburghCouncilConnector save method - data persistence"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "edinburgh_council": {
                "enabled": True,
                "api_key": None,
                "base_url": "https://data.edinburghcouncilmaps.info/datasets",
                "timeout_seconds": 30
            }
        }

        self.test_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": 1,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.1883, 55.9533]
                    },
                    "properties": {
                        "name": "Edinburgh Leisure Centre",
                        "facility_type": "Sports Centre"
                    }
                }
            ]
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.edinburgh_council.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_file(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method creates JSON file"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = EdinburghCouncilConnector()
        connector.db = mock_db

        file_path = await connector.save(
            self.test_data,
            "https://data.edinburghcouncilmaps.info/datasets/sports_facilities/query"
        )

        # Verify save_json was called
        mock_save_json.assert_called_once()
        self.assertIsInstance(file_path, str)
        self.assertIn("engine/data/raw/edinburgh_council/", file_path)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.edinburgh_council.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_database_record(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method creates RawIngestion database record"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = EdinburghCouncilConnector()
        connector.db = mock_db

        await connector.save(
            self.test_data,
            "https://data.edinburghcouncilmaps.info/datasets/sports_facilities/query"
        )

        # Verify database record was created
        mock_db.rawingestion.create.assert_called_once()
        call_args = mock_db.rawingestion.create.call_args

        # Check that required fields are present
        data_arg = call_args.kwargs['data']
        self.assertEqual(data_arg['source'], 'edinburgh_council')
        self.assertIn('source_url', data_arg)
        self.assertIn('file_path', data_arg)
        self.assertIn('hash', data_arg)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.edinburgh_council.save_json')
    @patch('prisma.Prisma')
    async def test_save_includes_feature_count_in_metadata(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save includes feature count in metadata"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config

        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = EdinburghCouncilConnector()
        connector.db = mock_db

        await connector.save(
            self.test_data,
            "https://data.edinburghcouncilmaps.info/datasets/sports_facilities/query"
        )

        # Check metadata includes feature count
        call_args = mock_db.rawingestion.create.call_args
        metadata_json = call_args.kwargs['data']['metadata_json']
        metadata = json.loads(metadata_json)

        self.assertIn('feature_count', metadata)
        self.assertEqual(metadata['feature_count'], 1)


class TestEdinburghCouncilConnectorDeduplication(unittest.IsolatedAsyncioTestCase):
    """Test EdinburghCouncilConnector deduplication logic"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "edinburgh_council": {
                "enabled": True,
                "api_key": None,
                "base_url": "https://data.edinburghcouncilmaps.info/datasets"
            }
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.edinburgh_council.check_duplicate')
    async def test_is_duplicate_checks_database(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate queries the database"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False

        connector = EdinburghCouncilConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("test_hash_123")

        # Verify check_duplicate was called
        mock_check_dup.assert_called_once_with(connector.db, "test_hash_123")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.edinburgh_council.check_duplicate')
    async def test_is_duplicate_returns_true_for_existing(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate returns True for existing content"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = True

        connector = EdinburghCouncilConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("existing_hash")

        self.assertTrue(result)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.edinburgh_council.check_duplicate')
    async def test_is_duplicate_returns_false_for_new(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate returns False for new content"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False

        connector = EdinburghCouncilConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("new_hash")

        self.assertFalse(result)


class TestEdinburghCouncilConnectorIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for complete fetch-save-deduplicate workflow"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "edinburgh_council": {
                "enabled": True,
                "api_key": None,
                "base_url": "https://data.edinburghcouncilmaps.info/datasets",
                "timeout_seconds": 30,
                "default_params": {
                    "outFields": "*",
                    "f": "geojson",
                    "returnGeometry": "true"
                }
            }
        }

        self.mock_response = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": 1,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.1883, 55.9533]
                    },
                    "properties": {
                        "name": "Test Facility",
                        "facility_type": "Sports Centre"
                    }
                }
            ]
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    @patch('engine.ingestion.edinburgh_council.save_json')
    @patch('engine.ingestion.edinburgh_council.check_duplicate')
    async def test_complete_workflow_fetch_and_save(
        self, mock_check_dup, mock_save_json, mock_session_class, mock_file, mock_yaml
    ):
        """Test complete workflow: fetch data, check duplicate, save"""
        from engine.ingestion.edinburgh_council import EdinburghCouncilConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False  # Not a duplicate

        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})

        connector = EdinburghCouncilConnector()
        connector.db = mock_db

        # Execute workflow
        data = await connector.fetch("sports_facilities")
        self.assertEqual(data, self.mock_response)

        file_path = await connector.save(
            data,
            "https://data.edinburghcouncilmaps.info/datasets/sports_facilities/query"
        )
        self.assertIn("edinburgh_council", file_path)


if __name__ == "__main__":
    unittest.main()
