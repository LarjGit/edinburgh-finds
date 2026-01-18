"""
Tests for OpenChargeMap API Connector

This module tests the OpenChargeMapConnector implementation which fetches
EV charging station data from the OpenChargeMap API.

The OpenChargeMap API provides EV charging station information including:
- Location data (latitude, longitude, address)
- Charging point details (connectors, power output, network)
- Availability and access information
- Pricing and payment methods

Test Coverage:
- Connector initialization and configuration
- API request formatting and execution (nearby search by lat/lng)
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


class TestOpenChargeMapConnectorInitialization(unittest.IsolatedAsyncioTestCase):
    """Test OpenChargeMapConnector initialization and basic properties"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        # Mock configuration
        self.mock_config = {
            "open_charge_map": {
                "enabled": True,
                "api_key": "test_ocm_api_key_123",
                "base_url": "https://api.openchargemap.io/v3",
                "timeout_seconds": 30,
                "rate_limits": {
                    "requests_per_minute": 60,
                    "requests_per_hour": 1000
                },
                "default_params": {
                    "countrycode": "GB",
                    "maxresults": 100
                }
            }
        }

    async def test_open_charge_map_connector_can_be_imported(self):
        """Test that OpenChargeMapConnector class can be imported"""
        try:
            from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector
            self.assertIsNotNone(OpenChargeMapConnector)
        except ImportError:
            self.fail("Failed to import OpenChargeMapConnector - implementation not yet created")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_open_charge_map_connector_can_be_instantiated(self, mock_file, mock_yaml):
        """Test that OpenChargeMapConnector can be instantiated with valid config"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        connector = OpenChargeMapConnector()
        self.assertIsNotNone(connector)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_open_charge_map_connector_has_correct_source_name(self, mock_file, mock_yaml):
        """Test that OpenChargeMapConnector provides source_name as 'open_charge_map'"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        connector = OpenChargeMapConnector()
        self.assertEqual(connector.source_name, "open_charge_map")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_open_charge_map_connector_loads_config(self, mock_file, mock_yaml):
        """Test that OpenChargeMapConnector loads configuration from sources.yaml"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        connector = OpenChargeMapConnector()

        # Verify configuration was loaded
        self.assertEqual(connector.api_key, "test_ocm_api_key_123")
        self.assertEqual(connector.base_url, "https://api.openchargemap.io/v3")

    async def test_open_charge_map_connector_raises_error_without_config(self):
        """Test that OpenChargeMapConnector raises error if config file missing"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        with patch('builtins.open', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                OpenChargeMapConnector()

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_open_charge_map_connector_raises_error_without_api_key(self, mock_file, mock_yaml):
        """Test that OpenChargeMapConnector raises error if API key not configured"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        # Config without API key
        invalid_config = {
            "open_charge_map": {
                "enabled": True,
                "api_key": None,
                "base_url": "https://api.openchargemap.io/v3"
            }
        }
        mock_yaml.return_value = invalid_config

        with self.assertRaises(ValueError) as context:
            OpenChargeMapConnector()

        # Check error message mentions API key configuration
        error_msg = str(context.exception).lower()
        self.assertTrue("api" in error_msg or "key" in error_msg or "configured" in error_msg)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_open_charge_map_connector_raises_error_with_placeholder_key(self, mock_file, mock_yaml):
        """Test that OpenChargeMapConnector raises error if API key is placeholder"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        # Config with placeholder key
        invalid_config = {
            "open_charge_map": {
                "enabled": True,
                "api_key": "YOUR_OPENCHARGEMAP_API_KEY_HERE",
                "base_url": "https://api.openchargemap.io/v3"
            }
        }
        mock_yaml.return_value = invalid_config

        with self.assertRaises(ValueError):
            OpenChargeMapConnector()


class TestOpenChargeMapConnectorFetch(unittest.IsolatedAsyncioTestCase):
    """Test OpenChargeMapConnector fetch method - nearby charging stations"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "open_charge_map": {
                "enabled": True,
                "api_key": "test_ocm_api_key_123",
                "base_url": "https://api.openchargemap.io/v3",
                "timeout_seconds": 30,
                "default_params": {
                    "countrycode": "GB",
                    "maxresults": 100
                }
            }
        }

        # Mock OpenChargeMap API response
        self.mock_api_response = [
            {
                "ID": 123456,
                "UUID": "abc123-def456-ghi789",
                "AddressInfo": {
                    "Title": "Edinburgh Charging Station",
                    "AddressLine1": "123 Princes Street",
                    "Town": "Edinburgh",
                    "Postcode": "EH1 1AA",
                    "Latitude": 55.9533,
                    "Longitude": -3.1883,
                    "CountryID": 1,
                    "Country": {
                        "ISOCode": "GB",
                        "Title": "United Kingdom"
                    }
                },
                "NumberOfPoints": 2,
                "UsageType": {
                    "IsPayAtLocation": True,
                    "Title": "Public"
                },
                "StatusType": {
                    "IsOperational": True,
                    "Title": "Operational"
                },
                "Connections": [
                    {
                        "ID": 1,
                        "ConnectionType": {
                            "Title": "Type 2 (Socket Only)"
                        },
                        "PowerKW": 22.0,
                        "CurrentType": {
                            "Title": "AC (Three-Phase)"
                        }
                    }
                ]
            },
            {
                "ID": 789012,
                "UUID": "xyz789-uvw012-rst345",
                "AddressInfo": {
                    "Title": "Leith Supercharger",
                    "AddressLine1": "456 Leith Walk",
                    "Town": "Edinburgh",
                    "Postcode": "EH6 2BB",
                    "Latitude": 55.9600,
                    "Longitude": -3.1700,
                    "CountryID": 1,
                    "Country": {
                        "ISOCode": "GB",
                        "Title": "United Kingdom"
                    }
                },
                "NumberOfPoints": 8,
                "UsageType": {
                    "IsPayAtLocation": False,
                    "Title": "Public - Membership Required"
                },
                "StatusType": {
                    "IsOperational": True,
                    "Title": "Operational"
                },
                "Connections": [
                    {
                        "ID": 2,
                        "ConnectionType": {
                            "Title": "Tesla (Model S/X)"
                        },
                        "PowerKW": 150.0,
                        "CurrentType": {
                            "Title": "DC"
                        }
                    }
                ]
            }
        ]

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_makes_api_request(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch method makes HTTP GET request to OpenChargeMap API"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        # Mock aiohttp session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_api_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = OpenChargeMapConnector()
        result = await connector.fetch("55.9533,-3.1883")

        # Verify API was called with GET
        mock_session.get.assert_called_once()
        self.assertEqual(result, self.mock_api_response)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_api_key(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes API key in request parameters"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_api_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = OpenChargeMapConnector()
        await connector.fetch("55.9533,-3.1883")

        # Verify API key was included in request parameters
        call_args = mock_session.get.call_args
        self.assertIn('params', call_args.kwargs)
        params = call_args.kwargs['params']
        self.assertIn('key', params)
        self.assertEqual(params['key'], "test_ocm_api_key_123")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_latitude_longitude(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes latitude and longitude in request parameters"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_api_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = OpenChargeMapConnector()
        await connector.fetch("55.9533,-3.1883")

        # Verify latitude and longitude were included
        call_args = mock_session.get.call_args
        params = call_args.kwargs['params']
        self.assertIn('latitude', params)
        self.assertIn('longitude', params)
        self.assertEqual(params['latitude'], '55.9533')
        self.assertEqual(params['longitude'], '-3.1883')

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_includes_default_params(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch includes default parameters from config"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_api_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = OpenChargeMapConnector()
        await connector.fetch("55.9533,-3.1883")

        # Verify default params were included
        call_args = mock_session.get.call_args
        params = call_args.kwargs['params']
        self.assertIn('countrycode', params)
        self.assertEqual(params['countrycode'], 'GB')
        self.assertIn('maxresults', params)
        self.assertEqual(params['maxresults'], 100)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_http_error(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch raises error on HTTP failure"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = OpenChargeMapConnector()

        with self.assertRaises(Exception):
            await connector.fetch("55.9533,-3.1883")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_network_timeout(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch handles network timeout gracefully"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector
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

        connector = OpenChargeMapConnector()

        with self.assertRaises(asyncio.TimeoutError):
            await connector.fetch("55.9533,-3.1883")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_handles_empty_results(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch handles API response with no results"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        # Mock API response with no results
        empty_response = []

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

        connector = OpenChargeMapConnector()
        result = await connector.fetch("55.9533,-3.1883")

        # Should return the response even with empty results
        self.assertEqual(result, empty_response)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    async def test_fetch_parses_lat_lng_from_query(self, mock_session_class, mock_file, mock_yaml):
        """Test that fetch correctly parses latitude,longitude from query string"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_api_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_class.return_value = mock_session

        connector = OpenChargeMapConnector()
        await connector.fetch("55.9533,-3.1883")

        # Verify parsing worked correctly
        call_args = mock_session.get.call_args
        params = call_args.kwargs['params']
        self.assertEqual(params['latitude'], '55.9533')
        self.assertEqual(params['longitude'], '-3.1883')

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_fetch_raises_error_on_invalid_coordinates(self, mock_file, mock_yaml):
        """Test that fetch raises error if coordinates are invalid format"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        connector = OpenChargeMapConnector()

        with self.assertRaises(ValueError):
            await connector.fetch("invalid-coordinates")


class TestOpenChargeMapConnectorSave(unittest.IsolatedAsyncioTestCase):
    """Test OpenChargeMapConnector save method - data persistence"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "open_charge_map": {
                "enabled": True,
                "api_key": "test_ocm_api_key_123",
                "base_url": "https://api.openchargemap.io/v3"
            }
        }

        self.test_data = [
            {
                "ID": 123456,
                "AddressInfo": {
                    "Title": "Edinburgh Charging Station",
                    "Latitude": 55.9533,
                    "Longitude": -3.1883
                }
            }
        ]

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_charge_map.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_file(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method creates JSON file"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = OpenChargeMapConnector()
        connector.db = mock_db

        file_path = await connector.save(
            self.test_data,
            "https://api.openchargemap.io/v3/poi/?latitude=55.9533&longitude=-3.1883"
        )

        # Verify save_json was called
        mock_save_json.assert_called_once()
        self.assertIsInstance(file_path, str)
        self.assertIn("engine/data/raw/open_charge_map/", file_path)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_charge_map.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_database_record(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method creates RawIngestion database record"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = OpenChargeMapConnector()
        connector.db = mock_db

        await connector.save(
            self.test_data,
            "https://api.openchargemap.io/v3/poi/?latitude=55.9533&longitude=-3.1883"
        )

        # Verify database record was created
        mock_db.rawingestion.create.assert_called_once()
        call_args = mock_db.rawingestion.create.call_args

        # Check that required fields are present
        data_arg = call_args.kwargs['data']
        self.assertEqual(data_arg['source'], 'open_charge_map')
        self.assertEqual(data_arg['source_url'], 'https://api.openchargemap.io/v3/poi/?latitude=55.9533&longitude=-3.1883')
        self.assertIn('file_path', data_arg)
        self.assertIn('hash', data_arg)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_charge_map.save_json')
    @patch('prisma.Prisma')
    async def test_save_returns_file_path(self, mock_prisma, mock_save_json, mock_file, mock_yaml):
        """Test that save method returns the file path"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config

        mock_db = AsyncMock()
        mock_db.rawingestion.create = AsyncMock(return_value={"id": 1})
        mock_prisma.return_value = mock_db

        connector = OpenChargeMapConnector()
        connector.db = mock_db

        file_path = await connector.save(
            self.test_data,
            "https://api.openchargemap.io/v3/poi/?latitude=55.9533&longitude=-3.1883"
        )

        self.assertIsInstance(file_path, str)
        self.assertIn(".json", file_path)
        self.assertIn("open_charge_map", file_path)


class TestOpenChargeMapConnectorDeduplication(unittest.IsolatedAsyncioTestCase):
    """Test OpenChargeMapConnector deduplication logic"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "open_charge_map": {
                "enabled": True,
                "api_key": "test_ocm_api_key_123",
                "base_url": "https://api.openchargemap.io/v3"
            }
        }

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_charge_map.check_duplicate')
    async def test_is_duplicate_checks_database(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate queries the database"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False

        connector = OpenChargeMapConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("test_hash_123")

        # Verify check_duplicate was called
        mock_check_dup.assert_called_once_with(connector.db, "test_hash_123")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_charge_map.check_duplicate')
    async def test_is_duplicate_returns_true_for_existing(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate returns True for existing content"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = True

        connector = OpenChargeMapConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("existing_hash")

        self.assertTrue(result)

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('engine.ingestion.connectors.open_charge_map.check_duplicate')
    async def test_is_duplicate_returns_false_for_new(self, mock_check_dup, mock_file, mock_yaml):
        """Test that is_duplicate returns False for new content"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

        mock_yaml.return_value = self.mock_config
        mock_check_dup.return_value = False

        connector = OpenChargeMapConnector()
        connector.db = AsyncMock()

        result = await connector.is_duplicate("new_hash")

        self.assertFalse(result)


class TestOpenChargeMapConnectorIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for complete fetch-save-deduplicate workflow"""

    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.mock_config = {
            "open_charge_map": {
                "enabled": True,
                "api_key": "test_ocm_api_key_123",
                "base_url": "https://api.openchargemap.io/v3",
                "default_params": {
                    "countrycode": "GB",
                    "maxresults": 100
                }
            }
        }

        self.mock_response = [
            {
                "ID": 123456,
                "AddressInfo": {
                    "Title": "Edinburgh Charging Station",
                    "Latitude": 55.9533,
                    "Longitude": -3.1883
                }
            }
        ]

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    @patch('aiohttp.ClientSession')
    @patch('engine.ingestion.connectors.open_charge_map.save_json')
    @patch('engine.ingestion.connectors.open_charge_map.check_duplicate')
    async def test_complete_workflow_fetch_and_save(
        self, mock_check_dup, mock_save_json, mock_session_class, mock_file, mock_yaml
    ):
        """Test complete workflow: fetch data, check duplicate, save"""
        from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector

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

        connector = OpenChargeMapConnector()
        connector.db = mock_db

        # Execute workflow
        data = await connector.fetch("55.9533,-3.1883")
        self.assertEqual(data, self.mock_response)

        file_path = await connector.save(
            data,
            "https://api.openchargemap.io/v3/poi/?latitude=55.9533&longitude=-3.1883"
        )
        self.assertIn("open_charge_map", file_path)


if __name__ == "__main__":
    unittest.main()
