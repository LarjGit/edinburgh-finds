# Engine Scripts

This directory contains manual test scripts and utilities for the data ingestion engine.

## Test Scripts

### `run_serper_connector.py`

Manual integration test for the Serper API connector. Tests the complete workflow:
- Configuration loading
- API request to Serper
- Response parsing
- Deduplication check
- Data persistence (filesystem + database)

**Setup:**

1. **Get a Serper API key**
   - Sign up at https://serper.dev/
   - Free tier: 2,500 searches/month
   - Copy your API key

2. **Create configuration file**
   ```bash
   cp engine/config/sources.yaml.example engine/config/sources.yaml
   ```

3. **Add your API key**
   - Open `engine/config/sources.yaml`
   - Replace `YOUR_SERPER_API_KEY_HERE` with your actual API key
   - Save the file

4. **Ensure database is set up**
   ```bash
   cd prisma
   npx prisma generate
   npx prisma db push
   cd ..
   ```

**Usage:**

```bash
python -m engine.scripts.run_serper_connector
```

**Expected Output:**

- ✓ Configuration validated
- ✓ API request successful (returns ~10 results for "padel edinburgh")
- ✓ Data saved to `engine/data/raw/serper/YYYYMMDD_*.json`
- ✓ Database record created in `RawIngestion` table
- ✓ Deduplication working (running again shows duplicate detected)

**Troubleshooting:**

- **"sources.yaml not found"**: Run step 2 above
- **"API key not configured"**: Check step 3 - ensure you replaced the placeholder
- **"Failed to connect to database"**: Run step 4 - Prisma needs to be set up
- **"401 Unauthorized"**: API key is invalid or expired
- **"429 Too Many Requests"**: You've exceeded your rate limit

**What the test verifies:**

1. Configuration loading and validation
2. API authentication and request formatting
3. Response parsing (organic results, credits, etc.)
4. Content hashing for deduplication
5. Filesystem storage (JSON files)
6. Database persistence (RawIngestion records)
7. Duplicate detection on re-run

**Files created:**

- `engine/data/raw/serper/YYYYMMDD_padel_edinburgh_<hash>.json` - Raw API response
- Database record in `RawIngestion` table with metadata

## Future Scripts

Additional test scripts will be added here for:
- Google Places connector testing
- OSM connector testing
- Batch ingestion workflows
- Data quality validation
