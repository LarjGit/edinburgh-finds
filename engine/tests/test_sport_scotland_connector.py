"""
Tests for SportScotland WFS Connector

This module tests the SportScotlandConnector implementation which fetches
sports facility data from the SportScotland WFS (Web Feature Service).

SportScotland provides comprehensive data about sports facilities across
Scotland through the Spatial Hub Scotland portal, including:
- 11 themed facility layers (pitches, tennis courts, swimming pools, etc.)
- Location data with coordinates
- Facility attributes (type, surface, size, capacity)
- Operational status and ownership information

Test Coverage:
- Connector initialization and configuration
- WFS GetFeature request formatting and execution
- GeoJSON response parsing and validation
- Spatial filtering (bbox for Edinburgh area)
- Layer selection (pitches, tennis courts, etc.)
- Data persistence to filesystem and database
- Deduplication logic
- Error handling (network, API, validation errors)
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime
import json
import os


class TestSportScotlandConnectorInitialization(unittest.IsolatedAsyncioTestCase):
    """Test SportScotlandConnector initialization and basic properties"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        # Mock configuration
        self.mock_config = {
            "sport_scotland": {
                "enabled": True,
                "api_key": None,  # WFS may not require API key
                "base_url": "https://data.spatialhub.scot/geoserver/sport_scotland/wfs",
                "timeout_seconds": 60,
                "default_params": {
                    "service": "WFS",
                    "version": "2.0.0",
                    "request": "GetFeature",
                    "outputFormat": "application/json",
                    "srsName": "EPSG:4326"
                },
                "edinburgh_bbox": {
                    "minx": -3.4,
                    "miny": 55.85,
                    "maxx": -3.0,
                    "maxy": 56.0
                }
            }
        }

    async def test_sport_scotland_connector_can_be_imported(self):
        """Test that SportScotlandConnector class can be imported"""
        try:
            from engine.ingestion.sport_scotland import SportScotlandConnector
            self.assertIsNotNone(SportScotlandConnector)
        except ImportError:
            self.fail("Failed to import SportScotlandConnector - implementation not yet created")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_sport_scotland_connector_can_be_instantiated(self, mock_file, mock_yaml):
        """Test that SportScotlandConnector can be instantiated with valid config"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        connector = SportScotlandConnector()
        self.assertIsNotNone(connector)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_sport_scotland_connector_has_correct_source_name(self, mock_file, mock_yaml):
        """Test that SportScotlandConnector provides source_name as 'sport_scotland'"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        connector = SportScotlandConnector()
        self.assertEqual(connector.source_name, "sport_scotland")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_sport_scotland_connector_loads_config(self, mock_file, mock_yaml):
        """Test that SportScotlandConnector loads configuration from sources.yaml"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        connector = SportScotlandConnector()

        # Verify configuration was loaded
        self.assertEqual(connector.base_url, "https://data.spatialhub.scot/geoserver/sport_scotland/wfs")
        self.assertEqual(connector.timeout, 60)

    async def test_sport_scotland_connector_raises_error_without_config(self):
        """Test that SportScotlandConnector raises error if config file missing"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        with patch('builtins.open', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                SportScotlandConnector()

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_sport_scotland_connector_loads_edinburgh_bbox(self, mock_file, mock_yaml):
        """Test that SportScotlandConnector loads Edinburgh bounding box from config"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        connector = SportScotlandConnector()

        # Verify bbox was loaded
        self.assertIsNotNone(connector.edinburgh_bbox)
        self.assertEqual(connector.edinburgh_bbox['minx'], -3.4)
        self.assertEqual(connector.edinburgh_bbox['maxy'], 56.0)


class TestSportScotlandConnectorFetch(unittest.IsolatedAsyncioTestCase):
    """Test SportScotlandConnector fetch method - WFS GetFeature requests"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "sport_scotland": {
                "enabled": True,
                "api_key": None,
                "base_url": "https://data.spatialhub.scot/geoserver/sport_scotland/wfs",
                "timeout_seconds": 60,
                "default_params": {
                    "service": "WFS",
                    "version": "2.0.0",
                    "request": "GetFeature",
                    "outputFormat": "application/json",
                    "srsName": "EPSG:4326"
                },
                "edinburgh_bbox": {
                    "minx": -3.4,
                    "miny": 55.85,
                    "maxx": -3.0,
                    "maxy": 56.0
                }
            }
        }

        # Mock WFS GeoJSON response
        self.mock_wfs_response = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": "pitches.1",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.1883, 55.9533]
                    },
                    "properties": {
                        "facility_name": "Murrayfield Stadium",
                        "facility_type": "Pitch",
                        "sport_type": "Rugby",
                        "surface": "Grass",
                        "ownership": "Scottish Rugby Union",
                        "postcode": "EH12 5PJ"
                    }
                },
                {
                    "type": "Feature",
                    "id": "pitches.2",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.2034, 55.9426]
                    },
                    "properties": {
                        "facility_name": "Easter Road Stadium",
                        "facility_type": "Pitch",
                        "sport_type": "Football",
                        "surface": "Grass",
                        "ownership": "Hibernian FC",
                        "postcode": "EH7 5QG"
                    }
                }
            ],
            "totalFeatures": 2,
            "numberMatched": 2,
            "numberReturned": 2,
            "crs": {
                "type": "name",
                "properties": {
                    "name": "urn:ogc:def:crs:EPSG::4326"
                }
            }
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_makes_wfs_request(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch method makes HTTP GET request to WFS endpoint"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        # Mock aiohttp session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_wfs_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = SportScotlandConnector()
        result = await connector.fetch("pitches")

        # Verify WFS API was called with GET
        mock_session.get.assert_called_once()
        self.assertEqual(result, self.mock_wfs_response)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_wfs_parameters(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes required WFS parameters"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_wfs_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = SportScotlandConnector()
        await connector.fetch("pitches")

        # Verify WFS parameters were included
        call_args = mock_session.get.call_args
        self.assertIn('params', call_args.kwargs)
        params = call_args.kwargs['params']

        self.assertEqual(params['service'], 'WFS')
        self.assertEqual(params['version'], '2.0.0')
        self.assertEqual(params['request'], 'GetFeature')
        self.assertEqual(params['outputFormat'], 'application/json')

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_layer_typename(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes typeName parameter for layer selection"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_wfs_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = SportScotlandConnector()
        await connector.fetch("tennis_courts")

        # Verify typeName was included
        call_args = mock_session.get.call_args
        params = call_args.kwargs['params']
        self.assertIn('typeName', params)
        self.assertEqual(params['typeName'], 'sh_sptk:tennis_courts')

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_bbox_filter(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes bbox parameter for Edinburgh spatial filter"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_wfs_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = SportScotlandConnector()
        await connector.fetch("pitches")

        # Verify bbox was included (minx,miny,maxx,maxy format)
        call_args = mock_session.get.call_args
        params = call_args.kwargs['params']
        self.assertIn('bbox', params)
        # Format: minx,miny,maxx,maxy[,crs]
        bbox = params['bbox']
        self.assertIn('-3.4', bbox)
        self.assertIn('55.85', bbox)
        self.assertIn('-3.0', bbox)
        self.assertIn('56.0', bbox)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_http_error(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch raises error on HTTP failure"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = SportScotlandConnector()

        with self.assertRaises(Exception):
            await connector.fetch("pitches")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_network_timeout(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch handles network timeout gracefully"""
        from engine.ingestion.sport_scotland import SportScotlandConnector
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

        connector = SportScotlandConnector()

        with self.assertRaises(asyncio.TimeoutError):
            await connector.fetch("pitches")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_empty_feature_collection(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch handles WFS response with no features"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        # Mock API response with no features
        empty_response = {
            "type": "FeatureCollection",
            "features": [],
            "totalFeatures": 0,
            "numberReturned": 0
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

        connector = SportScotlandConnector()
        result = await connector.fetch("padel_courts")

        # Should return the response even with empty features
        self.assertEqual(result, empty_response)
        self.assertEqual(len(result['features']), 0)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_fetch_raises_error_on_invalid_layer(self, mock_file, mock_yaml):
        """Test that fetch validates layer name"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        connector = SportScotlandConnector()

        # Test with empty layer name
        with self.assertRaises(ValueError):
            await connector.fetch("")


class TestSportScotlandConnectorSave(unittest.IsolatedAsyncioTestCase):
    """Test SportScotlandConnector save method - data persistence"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "sport_scotland": {
                "enabled": True,
                "api_key": None,
                "base_url": "https://data.spatialhub.scot/geoserver/sport_scotland/wfs",
                "timeout_seconds": 60
            }
        }

        self.test_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": "pitches.1",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.1883, 55.9533]
                    },
                    "properties": {
                        "facility_name": "Murrayfield Stadium",
                        "sport_type": "Rugby"
                    }
                }
            ],
            "totalFeatures": 1
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.sport_scotland.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_file(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method creates JSON file"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = SportScotlandConnector()
        connector.db = mock_db

        file_path = await connector.save(
            self.test_data,
            "https://data.spatialhub.scot/geoserver/sport_scotland/wfs?request=GetFeature&typeName=pitches"
        )

        # Verify save_json was called
        mock_save_json.assert_called_once()
        self.assertIsInstance(file_path, str)
        self.assertIn("engine/data/raw/sport_scotland/", file_path)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.sport_scotland.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_database_record(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method creates RawIngestion database record"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = SportScotlandConnector()
        connector.db = mock_db

        await connector.save(
            self.test_data,
            "https://data.spatialhub.scot/geoserver/sport_scotland/wfs?request=GetFeature&typeName=pitches"
        )

        # Verify database record was created
        mock_db.rawingestion.create.assert_called_once()
        call_args = mock_db.rawingestion.create.call_args

        # Check that required fields are present
        data_arg = call_args.kwargs['data']
        self.assertEqual(data_arg['source'], 'sport_scotland')
        self.assertIn('source_url', data_arg)
        self.assertIn('file_path', data_arg)
        self.assertIn('hash', data_arg)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.sport_scotland.save_json')
    @patch('prisma.Prisma')
    async def test_save_includes_feature_count_in_metadata(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save includes feature count in metadata"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config

        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = SportScotlandConnector()
        connector.db = mock_db

        await connector.save(
            self.test_data,
            "https://data.spatialhub.scot/geoserver/sport_scotland/wfs?request=GetFeature&typeName=pitches"
        )

        # Check metadata includes feature count
        call_args = mock_db.rawingestion.create.call_args
        metadata_json = call_args.kwargs['data']['metadata_json']
        metadata = json.loads(metadata_json)

        self.assertIn('feature_count', metadata)
        self.assertEqual(metadata['feature_count'], 1)


class TestSportScotlandConnectorDeduplication(unittest.IsolatedAsyncioTestCase):
    """Test SportScotlandConnector deduplication logic"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "sport_scotland": {
                "enabled": True,
                "api_key": None,
                "base_url": "https://data.spatialhub.scot/geoserver/sport_scotland/wfs"
            }
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.sport_scotland.check_duplicate')
    async def test_is_duplicate_checks_database(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate queries the database"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False

        connector = SportScotlandConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("test_hash_123")

        # Verify check_duplicate was called
        mock_check_dup.assert_called_once_with(connector.db, "test_hash_123")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.sport_scotland.check_duplicate')
    async def test_is_duplicate_returns_true_for_existing(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate returns True for existing content"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = True

        connector = SportScotlandConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("existing_hash")

        self.assertTrue(result)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.sport_scotland.check_duplicate')
    async def test_is_duplicate_returns_false_for_new(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate returns False for new content"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False

        connector = SportScotlandConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("new_hash")

        self.assertFalse(result)


class TestSportScotlandConnectorIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for complete fetch-save-deduplicate workflow"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "sport_scotland": {
                "enabled": True,
                "api_key": None,
                "base_url": "https://data.spatialhub.scot/geoserver/sport_scotland/wfs",
                "timeout_seconds": 60,
                "default_params": {
                    "service": "WFS",
                    "version": "2.0.0",
                    "request": "GetFeature",
                    "outputFormat": "application/json",
                    "srsName": "EPSG:4326"
                },
                "edinburgh_bbox": {
                    "minx": -3.4,
                    "miny": 55.85,
                    "maxx": -3.0,
                    "maxy": 56.0
                }
            }
        }

        self.mock_response = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": "tennis_courts.1",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-3.1883, 55.9533]
                    },
                    "properties": {
                        "facility_name": "Edinburgh Tennis Club",
                        "sport_type": "Tennis",
                        "surface": "Hard Court"
                    }
                }
            ],
            "totalFeatures": 1
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    @patch('engine.ingestion.sport_scotland.save_json')
    @patch('engine.ingestion.sport_scotland.check_duplicate')
    async def test_complete_workflow_fetch_and_save(
        self, mock_check_dup, mock_save_json, mock_session_class, mock_file, mock_yaml
    ):
        """Test complete workflow: fetch WFS data, check duplicate, save"""
        from engine.ingestion.sport_scotland import SportScotlandConnector

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

        connector = SportScotlandConnector()
        connector.db = mock_db

        # Execute workflow
        data = await connector.fetch("tennis_courts")
        self.assertEqual(data, self.mock_response)

        file_path = await connector.save(
            data,
            "https://data.spatialhub.scot/geoserver/sport_scotland/wfs?request=GetFeature&typeName=tennis_courts"
        )
        self.assertIn("sport_scotland", file_path)


if __name__ == "__main__":
    unittest.main()
