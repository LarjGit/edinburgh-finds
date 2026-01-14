# Connector Development Guide

Complete guide for adding new data source connectors to the ingestion pipeline.

**Last Updated:** 2026-01-14
**Author:** Edinburgh Finds Development Team

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Step-by-Step Guide](#step-by-step-guide)
5. [API Patterns](#api-patterns)
6. [Testing Requirements](#testing-requirements)
7. [Configuration](#configuration)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Examples](#examples)

---

## Overview

### What is a Connector?

A connector is a Python module that:
- Fetches raw data from an external source (API, web service, database)
- Saves data to the filesystem in JSON format
- Creates metadata records in the `RawIngestion` database table
- Implements deduplication to prevent re-ingesting identical data

### When to Add a Connector

Add a new connector when you need to:
- Integrate a new data source (API, WFS, scraper)
- Enrich venue listings with supplementary data
- Cross-reference with authoritative datasets
- Gather data for later structured extraction

---

## Architecture

### BaseConnector Interface

All connectors must inherit from `BaseConnector` and implement four methods:

```python
from engine.ingestion.base import BaseConnector

class MyConnector(BaseConnector):
    @property
    def source_name(self) -> str:
        """Unique identifier for this source (e.g., 'my_source')"""
        pass

    async def fetch(self, query: str) -> dict:
        """Fetch data from the external source"""
        pass

    async def save(self, data: dict, source_url: str) -> str:
        """Save data to filesystem and create DB record"""
        pass

    async def is_duplicate(self, content_hash: str) -> bool:
        """Check if content hash already exists"""
        pass
```

### Data Flow

```
┌─────────────┐
│   Connector │
└──────┬──────┘
       │
       ├─ 1. fetch(query)
       │    └─> HTTP/WFS/API call
       │
       ├─ 2. compute_content_hash(data)
       │    └─> SHA-256 hash
       │
       ├─ 3. is_duplicate(hash)
       │    └─> Query RawIngestion table
       │
       └─ 4. save(data, url)
            ├─> Save JSON to filesystem
            └─> Create DB record
```

### Directory Structure

```
engine/
├── ingestion/
│   ├── base.py                 # BaseConnector interface
│   ├── storage.py              # Filesystem helpers
│   ├── deduplication.py        # Hash utilities
│   ├── serper.py              # Example: REST API
│   ├── sport_scotland.py      # Example: WFS
│   └── my_connector.py        # Your new connector
├── tests/
│   └── test_my_connector.py   # Unit tests
├── scripts/
│   └── test_my_connector.py   # Manual test script
└── config/
    └── sources.yaml           # Configuration
```

---

## Quick Start

**Time estimate:** 2-4 hours for a simple REST API connector

### 1. Create Test File (10 mins)

```bash
# Create test file
touch engine/tests/test_my_connector.py
```

### 2. Write Failing Tests (30 mins)

Follow TDD: Write tests first, then implement.

```python
"""Tests for MyConnector"""
import unittest
from unittest.mock import AsyncMock, patch

class TestMyConnectorInitialization(unittest.IsolatedAsyncioTestCase):
    async def test_my_connector_can_be_imported(self):
        from engine.ingestion.my_connector import MyConnector
        self.assertIsNotNone(MyConnector)

    # Add 15-20 more tests...
```

### 3. Implement Connector (60-90 mins)

```python
"""MyConnector - Fetch data from MySource API"""
import aiohttp
from engine.ingestion.base import BaseConnector

class MyConnector(BaseConnector):
    def __init__(self, config_path: str = "engine/config/sources.yaml"):
        # Load config, validate API key
        pass

    @property
    def source_name(self) -> str:
        return "my_source"

    async def fetch(self, query: str) -> dict:
        # Make API call
        pass

    async def save(self, data: dict, source_url: str) -> str:
        # Save to filesystem + DB
        pass

    async def is_duplicate(self, content_hash: str) -> bool:
        # Check for duplicates
        pass
```

### 4. Run Tests (5 mins)

```bash
python -m unittest engine.tests.test_my_connector -v
```

### 5. Manual Testing (30 mins)

Create and run manual test script with real API.

### 6. Documentation (15 mins)

Add configuration to `sources.yaml`, update this guide with examples.

---

## Step-by-Step Guide

### Step 1: Research the Data Source

**Before coding, understand the API:**

1. **Read API documentation**
   - Authentication method (API key, OAuth, JWT, none)
   - Request format (GET, POST, query params, body)
   - Response format (JSON, XML, GeoJSON, GML)
   - Rate limits and quotas

2. **Test API manually**
   ```bash
   # Example: Test with curl
   curl "https://api.example.com/data?key=YOUR_KEY&query=edinburgh"
   ```

3. **Examine response structure**
   - What fields are available?
   - How is location data formatted?
   - Are there pagination or size limits?

4. **Check licensing**
   - Is the data open/public?
   - What attribution is required?
   - Any usage restrictions?

### Step 2: Write Tests (TDD Red Phase)

**Create comprehensive test file:**

```python
"""
Tests for MyConnector

Test Coverage:
- Initialization and configuration
- API request formatting
- Response parsing
- Data persistence
- Deduplication
- Error handling
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import json

class TestMyConnectorInitialization(unittest.IsolatedAsyncioTestCase):
    """Test connector initialization and configuration"""

    async def asyncSetUp(self):
        self.mock_config = {
            "my_source": {
                "enabled": True,
                "api_key": "test_key_123",
                "base_url": "https://api.example.com",
                "timeout_seconds": 30
            }
        }

    async def test_connector_can_be_imported(self):
        """Test that connector class can be imported"""
        try:
            from engine.ingestion.my_connector import MyConnector
            self.assertIsNotNone(MyConnector)
        except ImportError:
            self.fail("Failed to import MyConnector")

    @patch('yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open)
    async def test_connector_loads_config(self, mock_file, mock_yaml):
        """Test that connector loads configuration"""
        from engine.ingestion.my_connector import MyConnector
        mock_yaml.return_value = self.mock_config

        connector = MyConnector()
        self.assertEqual(connector.source_name, "my_source")
        self.assertEqual(connector.api_key, "test_key_123")


class TestMyConnectorFetch(unittest.IsolatedAsyncioTestCase):
    """Test fetch method - API requests"""

    async def test_fetch_makes_api_request(self):
        """Test that fetch makes HTTP request"""
        # Mock aiohttp.ClientSession
        # Test API call
        pass

    async def test_fetch_includes_api_key(self):
        """Test that API key is included in request"""
        pass

    async def test_fetch_handles_http_error(self):
        """Test error handling for HTTP failures"""
        pass


class TestMyConnectorSave(unittest.IsolatedAsyncioTestCase):
    """Test save method - data persistence"""

    @patch('engine.ingestion.my_connector.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_file(self, mock_prisma, mock_save_json):
        """Test that save creates JSON file"""
        pass

    @patch('engine.ingestion.my_connector.save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_database_record(self, mock_prisma, mock_save_json):
        """Test that save creates RawIngestion record"""
        pass


class TestMyConnectorDeduplication(unittest.IsolatedAsyncioTestCase):
    """Test deduplication logic"""

    @patch('engine.ingestion.my_connector.check_duplicate')
    async def test_is_duplicate_checks_database(self, mock_check_dup):
        """Test that is_duplicate queries database"""
        pass


# Aim for 20-25 tests total
```

**Run tests (they should fail):**

```bash
python -m unittest engine.tests.test_my_connector -v
# Expected: All tests fail (module doesn't exist yet)
```

### Step 3: Implement Connector (TDD Green Phase)

**Create connector file:**

```python
"""
MyConnector - Fetch data from MySource API

This module implements MyConnector for fetching [description] data
from the MySource API.

API Documentation: https://api.example.com/docs
"""

import os
import json
import yaml
import aiohttp
from typing import Dict, Any
from datetime import datetime
from prisma import Prisma

from engine.ingestion.base import BaseConnector
from engine.ingestion.storage import generate_file_path, save_json
from engine.ingestion.deduplication import compute_content_hash, check_duplicate


class MyConnector(BaseConnector):
    """
    Connector for MySource API.

    Configuration:
        Loads from engine/config/sources.yaml:
        - api_key (required)
        - base_url
        - timeout_seconds
        - default_params

    Usage:
        connector = MyConnector()
        await connector.db.connect()

        data = await connector.fetch("edinburgh")
        content_hash = compute_content_hash(data)

        if not await connector.is_duplicate(content_hash):
            file_path = await connector.save(data, source_url)

        await connector.db.disconnect()
    """

    def __init__(self, config_path: str = "engine/config/sources.yaml"):
        """
        Initialize connector with configuration.

        Args:
            config_path: Path to sources.yaml

        Raises:
            FileNotFoundError: If config missing
            ValueError: If API key invalid
        """
        # Load configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        if 'my_source' not in config:
            raise ValueError("MySource config not found in sources.yaml")

        source_config = config['my_source']

        # Validate API key
        self.api_key = source_config.get('api_key')
        if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
            raise ValueError("MySource API key not configured")

        # Load other configuration
        self.base_url = source_config.get('base_url', 'https://api.example.com')
        self.timeout = source_config.get('timeout_seconds', 30)
        self.default_params = source_config.get('default_params', {})

        # Initialize database
        self.db = Prisma()

    @property
    def source_name(self) -> str:
        """Unique identifier for this source"""
        return "my_source"

    async def fetch(self, query: str) -> Dict[str, Any]:
        """
        Fetch data from MySource API.

        Args:
            query: Search query

        Returns:
            dict: Raw API response

        Raises:
            aiohttp.ClientError: Network errors
            asyncio.TimeoutError: Timeout
            Exception: HTTP errors
        """
        # Build request
        params = {
            'q': query,
            'key': self.api_key,
            **self.default_params
        }

        # Make API call
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API failed: {response.status}: {error_text}")

                return await response.json()

    async def save(self, data: Dict[str, Any], source_url: str) -> str:
        """
        Save data to filesystem and database.

        Args:
            data: Raw data from API
            source_url: Original request URL

        Returns:
            str: File path where saved
        """
        # Compute hash
        content_hash = compute_content_hash(data)

        # Extract metadata
        result_count = len(data.get('results', []))
        query = data.get('query', 'unknown')

        # Generate file path
        record_id = f"{query.replace(' ', '_')[:30]}_{content_hash[:8]}"
        file_path = generate_file_path(self.source_name, record_id)

        # Save JSON
        save_json(file_path, data)

        # Create DB record
        metadata = {
            'result_count': result_count,
            'query': query
        }

        await self.db.rawingestion.create(
            data={
                'source': self.source_name,
                'source_url': source_url,
                'file_path': file_path,
                'hash': content_hash,
                'status': 'success',
                'ingested_at': datetime.now(),
                'metadata_json': json.dumps(metadata)
            }
        )

        return file_path

    async def is_duplicate(self, content_hash: str) -> bool:
        """Check if content already ingested"""
        return await check_duplicate(self.db, content_hash)
```

**Run tests (they should pass):**

```bash
python -m unittest engine.tests.test_my_connector -v
# Expected: All tests pass
```

### Step 4: Add Configuration

**Update `engine/config/sources.yaml`:**

```yaml
my_source:
  # MySource API - [Description]
  # Get API key: https://example.com/api/keys
  enabled: true
  api_key: "YOUR_API_KEY_HERE"
  base_url: "https://api.example.com"
  timeout_seconds: 30
  rate_limits:
    requests_per_minute: 60
    requests_per_hour: 1000
  default_params:
    format: "json"
    limit: 100
```

### Step 5: Create Manual Test Script

**Create `engine/scripts/test_my_connector.py`:**

```python
"""
Manual Test Script for MyConnector

Prerequisites:
1. Add API key to engine/config/sources.yaml
2. Ensure database migrated (prisma generate && prisma db push)

Usage:
    python -m engine.scripts.test_my_connector
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def test_my_connector():
    """Test MyConnector with real API"""
    print("=" * 70)
    print("MYCONNECTOR MANUAL TEST")
    print("=" * 70)
    print()

    from engine.ingestion.my_connector import MyConnector
    from engine.ingestion.deduplication import compute_content_hash

    # Initialize
    connector = MyConnector()
    await connector.db.connect()
    print("✓ Connector initialized")
    print(f"  - Source: {connector.source_name}")
    print(f"  - Base URL: {connector.base_url}")
    print()

    # Fetch data
    query = "edinburgh"
    print(f"🔍 Fetching data: {query}")
    try:
        data = await connector.fetch(query)
        print(f"✓ API request successful")
        print(f"  - Results: {len(data.get('results', []))}")
        print()
    except Exception as e:
        print(f"❌ Error: {e}")
        await connector.db.disconnect()
        return False

    # Check duplicates
    content_hash = compute_content_hash(data)
    is_dup = await connector.is_duplicate(content_hash)
    if is_dup:
        print("⚠️  Duplicate detected")
    else:
        print("✓ No duplicate found")
    print()

    # Save data
    source_url = f"{connector.base_url}/search?q={query}"
    file_path = await connector.save(data, source_url)
    print(f"✓ Data saved: {file_path}")
    print()

    await connector.db.disconnect()
    print("✅ TEST COMPLETED SUCCESSFULLY")
    return True


def main():
    try:
        success = asyncio.run(test_my_connector())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Step 6: Test with Real API

```bash
# Get API key from provider
# Add to sources.yaml

# Run manual test
python -m engine.scripts.test_my_connector

# Expected output:
# ✓ Connector initialized
# ✓ API request successful
# ✓ Data saved
# ✅ TEST COMPLETED SUCCESSFULLY
```

### Step 7: Commit with TDD Workflow

```bash
# Commit tests
git add engine/tests/test_my_connector.py
git commit -m "test(ingestion): Add tests for MyConnector"

# Commit implementation
git add engine/ingestion/my_connector.py
git commit -m "feat(ingestion): Implement MyConnector"

# Commit manual test
git add engine/scripts/test_my_connector.py
git commit -m "test(ingestion): Add manual test for MyConnector with real API"
```

---

## API Patterns

### Pattern 1: REST API (JSON Response)

**Examples:** Serper, Google Places, OpenChargeMap

**Characteristics:**
- HTTP GET/POST requests
- JSON response format
- Query parameters or request body
- API key in header or query param

**Template:**

```python
async def fetch(self, query: str) -> Dict[str, Any]:
    params = {'q': query, 'key': self.api_key}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{self.base_url}/endpoint",
            params=params,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            return await response.json()
```

### Pattern 2: WFS (GeoJSON Response)

**Examples:** SportScotland

**Characteristics:**
- OGC Web Feature Service protocol
- GetFeature requests
- GeoJSON or GML response
- Spatial filtering (bbox)
- Workspace:layer naming

**Template:**

```python
async def fetch(self, layer: str) -> Dict[str, Any]:
    params = {
        'service': 'WFS',
        'version': '2.0.0',
        'request': 'GetFeature',
        'typeName': f'{self.workspace}:{layer}',
        'outputFormat': 'application/json',
        'bbox': self._build_bbox()
    }

    if self.api_key:
        params['authkey'] = self.api_key

    async with aiohttp.ClientSession() as session:
        async with session.get(
            self.base_url,
            params=params,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as response:
            if response.status != 200:
                raise Exception(f"WFS error: {response.status}")
            return await response.json()  # GeoJSON FeatureCollection
```

### Pattern 3: GraphQL API

**Characteristics:**
- POST request with query in body
- Single endpoint
- Nested response structure

**Template:**

```python
async def fetch(self, query_string: str) -> Dict[str, Any]:
    graphql_query = {
        "query": """
            query($search: String!) {
                facilities(search: $search) {
                    id
                    name
                    location { lat lon }
                }
            }
        """,
        "variables": {"search": query_string}
    }

    headers = {
        'Authorization': f'Bearer {self.api_key}',
        'Content-Type': 'application/json'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{self.base_url}/graphql",
            json=graphql_query,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as response:
            if response.status != 200:
                raise Exception(f"GraphQL error: {response.status}")
            result = await response.json()
            return result['data']
```

### Pattern 4: ArcGIS REST API

**Characteristics:**
- Feature Service endpoints
- Query parameters for spatial/attribute filters
- JSON or GeoJSON response

**Template:**

```python
async def fetch(self, where_clause: str = "1=1") -> Dict[str, Any]:
    params = {
        'where': where_clause,
        'outFields': '*',
        'f': 'geojson',
        'returnGeometry': 'true',
        'spatialRel': 'esriSpatialRelIntersects'
    }

    if self.api_key:
        params['token'] = self.api_key

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{self.base_url}/query",
            params=params,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as response:
            if response.status != 200:
                raise Exception(f"ArcGIS error: {response.status}")
            return await response.json()
```

---

## Testing Requirements

### Unit Test Coverage

**Minimum test count:** 20-25 tests per connector

**Test categories:**

1. **Initialization (5-6 tests)**
   - Import test
   - Instantiation
   - Config loading
   - API key validation
   - Missing config errors

2. **Fetch method (8-10 tests)**
   - Successful API call
   - Request parameter validation
   - Authentication inclusion
   - HTTP error handling
   - Timeout handling
   - Empty response handling
   - Query validation

3. **Save method (3-4 tests)**
   - File creation
   - Database record creation
   - Metadata inclusion
   - File path format

4. **Deduplication (3 tests)**
   - Database query
   - Returns True for existing
   - Returns False for new

5. **Integration (1-2 tests)**
   - Complete workflow
   - Error recovery

### Test Structure

```python
class Test[Connector]Initialization(unittest.IsolatedAsyncioTestCase):
    """Test connector initialization"""

    async def asyncSetUp(self):
        """Set up mock config"""
        self.mock_config = {...}


class Test[Connector]Fetch(unittest.IsolatedAsyncioTestCase):
    """Test fetch method"""

    @patch('aiohttp.ClientSession')
    async def test_fetch_makes_request(self, mock_session):
        """Test API request"""
        # Mock HTTP response
        # Test fetch method
        pass


class Test[Connector]Save(unittest.IsolatedAsyncioTestCase):
    """Test save method"""

    @patch('engine.ingestion.[connector].save_json')
    @patch('prisma.Prisma')
    async def test_save_creates_file(self, mock_prisma, mock_save):
        """Test file creation"""
        pass


class Test[Connector]Deduplication(unittest.IsolatedAsyncioTestCase):
    """Test deduplication"""

    @patch('engine.ingestion.[connector].check_duplicate')
    async def test_is_duplicate(self, mock_check):
        """Test duplicate check"""
        pass


class Test[Connector]Integration(unittest.IsolatedAsyncioTestCase):
    """Integration tests"""

    async def test_complete_workflow(self):
        """Test fetch → save → deduplicate"""
        pass
```

### Running Tests

```bash
# Run all connector tests
python -m unittest engine.tests.test_my_connector -v

# Run specific test class
python -m unittest engine.tests.test_my_connector.TestMyConnectorFetch -v

# Run single test
python -m unittest engine.tests.test_my_connector.TestMyConnectorFetch.test_fetch_makes_request -v

# Check coverage target: >80%
```

---

## Configuration

### sources.yaml Structure

```yaml
my_source:
  # Human-readable description
  # Documentation URL
  enabled: true | false

  # Authentication
  api_key: "YOUR_KEY_HERE" | null

  # Endpoint configuration
  base_url: "https://api.example.com"
  timeout_seconds: 30

  # Rate limiting
  rate_limits:
    requests_per_minute: 60
    requests_per_hour: 1000

  # Source-specific parameters
  default_params:
    param1: value1
    param2: value2

  # Optional: Spatial filtering
  edinburgh_bbox:
    minx: -3.4
    miny: 55.85
    maxx: -3.0
    maxy: 56.0
```

### Configuration Best Practices

1. **Never commit API keys**
   - sources.yaml is gitignored
   - Use placeholder values in templates
   - Document where to get keys

2. **Set appropriate timeouts**
   - REST APIs: 30s
   - WFS services: 60s
   - Slow APIs: 120s

3. **Configure rate limits**
   - Check API documentation
   - Set conservative limits
   - Monitor usage

4. **Use sensible defaults**
   - Common parameters in config
   - Override in code when needed

---

## Best Practices

### Code Quality

1. **Follow existing patterns**
   - Use aiohttp for async HTTP
   - Use yaml.safe_load for config
   - Use Prisma for database

2. **Comprehensive error handling**
   ```python
   try:
       data = await self.fetch(query)
   except aiohttp.ClientError as e:
       # Network error
       raise
   except asyncio.TimeoutError:
       # Timeout
       raise
   except Exception as e:
       # Other errors
       raise
   ```

3. **Validate inputs**
   ```python
   if not query or query.strip() == "":
       raise ValueError("Query cannot be empty")

   if not self.api_key:
       raise ValueError("API key required")
   ```

4. **Add comprehensive docstrings**
   - Module-level docstring with API docs link
   - Class docstring with usage example
   - Method docstrings with args/returns/raises

### Performance

1. **Use async/await**
   - All I/O operations async
   - Use aiohttp, not requests
   - Proper async context managers

2. **Implement deduplication**
   - Prevents duplicate API calls
   - Saves storage space
   - Reduces processing time

3. **Batch when possible**
   - Some APIs support bulk queries
   - Reduces total API calls

### Security

1. **Never log API keys**
   ```python
   # Good
   print(f"API key: {'*' * 20}")

   # Bad
   print(f"API key: {self.api_key}")
   ```

2. **Use HTTPS only**
   ```python
   if not self.base_url.startswith('https://'):
       raise ValueError("HTTPS required")
   ```

3. **Validate responses**
   ```python
   if response.status != 200:
       # Don't include full response in logs
       raise Exception(f"HTTP {response.status}")
   ```

### Maintainability

1. **Keep connectors independent**
   - No dependencies between connectors
   - Each can be tested in isolation

2. **Use helper functions**
   ```python
   def _parse_coordinates(self, data: dict) -> tuple:
       """Extract lat/lng from API response"""
       return (data['lat'], data['lng'])

   def _build_request_url(self, endpoint: str) -> str:
       """Build full URL for endpoint"""
       return f"{self.base_url}/{endpoint}"
   ```

3. **Document quirks**
   ```python
   # Note: API returns coordinates in lng,lat order (not lat,lng)
   coords = [data['longitude'], data['latitude']]
   ```

---

## Troubleshooting

### Common Issues

#### Issue: Tests fail with import error

```
ModuleNotFoundError: No module named 'engine.ingestion.my_connector'
```

**Solution:** Create connector file first, even if empty:

```bash
touch engine/ingestion/my_connector.py
```

#### Issue: API key validation fails

```
ValueError: API key not configured
```

**Solution:** Check sources.yaml:

```yaml
my_source:
  api_key: "actual_key_not_placeholder"
```

#### Issue: HTTP 401 Unauthorized

```
Exception: API failed: 401: Unauthorized
```

**Solutions:**
1. Verify API key is correct
2. Check if key is in correct location (header vs query param)
3. Verify key has required permissions

#### Issue: HTTP 429 Too Many Requests

```
Exception: API failed: 429: Rate limit exceeded
```

**Solutions:**
1. Implement rate limiting
2. Add delays between requests
3. Use exponential backoff

#### Issue: Timeout errors

```
asyncio.TimeoutError
```

**Solutions:**
1. Increase timeout value
2. Check network connectivity
3. Verify API endpoint is responding

#### Issue: Empty results

```
Features: 0
```

**Solutions:**
1. Check query format
2. Verify spatial filter (bbox)
3. Test query manually with curl
4. Check API documentation for query syntax

#### Issue: Coordinate system mismatch

```
No results despite valid data existing
```

**Solution:** Verify coordinate systems match:

```python
# API uses EPSG:27700 (British National Grid)
# Need to convert from EPSG:4326 (WGS84)
edinburgh_bbox:
  minx: 315000  # meters, not degrees
  miny: 665000
  maxx: 335000
  maxy: 680000
```

### Debugging Tips

1. **Use manual curl tests**
   ```bash
   curl -v "https://api.example.com/endpoint?key=YOUR_KEY&q=test"
   ```

2. **Add debug logging**
   ```python
   print(f"Request URL: {url}")
   print(f"Parameters: {params}")
   print(f"Response status: {response.status}")
   ```

3. **Check API documentation**
   - Verify endpoint URLs
   - Check parameter names
   - Review example responses

4. **Test incrementally**
   - Start with simple query
   - Add complexity gradually
   - Verify each step works

---

## Examples

### Example 1: Simple REST API (OpenChargeMap)

**Characteristics:**
- REST API with JSON response
- API key in query parameter
- Coordinate-based query

**Key code:**

```python
async def fetch(self, query: str) -> List[Dict[str, Any]]:
    # Parse coordinates
    lat, lng = query.split(',')

    # Build parameters
    params = {
        'key': self.api_key,
        'latitude': lat.strip(),
        'longitude': lng.strip(),
        **self.default_params
    }

    # Make request
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{self.base_url}/poi/",
            params=params,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as response:
            if response.status != 200:
                raise Exception(f"API error: {response.status}")
            return await response.json()
```

### Example 2: WFS with Authentication (SportScotland)

**Characteristics:**
- OGC WFS protocol
- JWT token authentication
- British National Grid coordinates
- GeoJSON response

**Key code:**

```python
async def fetch(self, layer: str) -> Dict[str, Any]:
    # Build WFS parameters
    params = {
        'service': 'WFS',
        'version': '2.0.0',
        'request': 'GetFeature',
        'typeName': f'sh_sptk:{layer}',
        'outputFormat': 'application/json',
        'bbox': f"{minx},{miny},{maxx},{maxy}"
    }

    # Add authentication
    if self.api_key:
        params['authkey'] = self.api_key

    # Make request
    async with aiohttp.ClientSession() as session:
        async with session.get(
            self.base_url,
            params=params,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as response:
            if response.status != 200:
                raise Exception(f"WFS error: {response.status}")
            return await response.json()  # GeoJSON
```

### Example 3: Search API with Pagination

**Template for paginated APIs:**

```python
async def fetch(self, query: str, max_pages: int = 5) -> Dict[str, Any]:
    """Fetch all pages of results"""
    all_results = []
    page = 1

    while page <= max_pages:
        params = {
            'q': query,
            'page': page,
            'per_page': 100,
            'key': self.api_key
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    raise Exception(f"API error: {response.status}")

                data = await response.json()
                results = data.get('results', [])

                if not results:
                    break  # No more results

                all_results.extend(results)

                if len(results) < 100:
                    break  # Last page

                page += 1

    return {'results': all_results, 'total': len(all_results)}
```

---

## Checklist

Use this checklist when adding a new connector:

### Planning
- [ ] Research API documentation
- [ ] Test API manually with curl/browser
- [ ] Understand authentication method
- [ ] Identify response format
- [ ] Check rate limits and quotas
- [ ] Verify data licensing

### Implementation
- [ ] Create test file
- [ ] Write 20-25 unit tests
- [ ] Run tests (verify they fail)
- [ ] Create connector file
- [ ] Implement `__init__` with config loading
- [ ] Implement `source_name` property
- [ ] Implement `fetch` method
- [ ] Implement `save` method
- [ ] Implement `is_duplicate` method
- [ ] Run tests (verify they pass)
- [ ] Add configuration to sources.yaml
- [ ] Create manual test script
- [ ] Test with real API
- [ ] Verify data saved correctly
- [ ] Check database records created
- [ ] Test deduplication works

### Documentation
- [ ] Add module docstring
- [ ] Add class docstring with usage example
- [ ] Add method docstrings
- [ ] Document configuration options
- [ ] Add example to this guide
- [ ] Update sources.yaml with comments

### Quality
- [ ] Test coverage >80%
- [ ] All tests pass
- [ ] No linting errors
- [ ] Error handling comprehensive
- [ ] Input validation present
- [ ] No hardcoded credentials

### Git
- [ ] Commit tests first
- [ ] Commit implementation
- [ ] Commit configuration
- [ ] Commit manual test
- [ ] Add git notes with details

---

## Summary

Adding a new connector involves:

1. **Research** the API (30 mins)
2. **Write tests** following TDD (30 mins)
3. **Implement** connector (60-90 mins)
4. **Configure** sources.yaml (10 mins)
5. **Test** with real API (30 mins)
6. **Document** and commit (15 mins)

**Total time:** 2-4 hours for a typical REST API connector

**Key principles:**
- Test-Driven Development (TDD)
- Follow existing patterns
- Comprehensive error handling
- Clear documentation
- Security-conscious coding

---

**Next Steps:**

After creating a connector:
1. Add it to the conductor plan
2. Consider rate limiting (Phase 4)
3. Add monitoring/logging (Phase 4)
4. Plan for extraction phase (Phase 2 of overall pipeline)

---

**Questions or issues?**

- Check existing connectors for examples
- Review this guide
- Test incrementally
- Ask for help when stuck

**Happy coding!** 🚀
