import hashlib
from pathlib import Path
import shutil
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from engine.ingestion.connectors.overture_release import OvertureReleaseConnector


def _getting_data_html() -> str:
    return """
    <html>
      <body>
        <a href=\"https://overturemaps-us-west-2.s3.amazonaws.com/release/2026-01-10.0/\">old</a>
        <a href=\"https://overturemaps-us-west-2.s3.amazonaws.com/release/2026-02-01.0/\">latest</a>
      </body>
    </html>
    """


def _places_listing_xml() -> str:
    return """
    <ListBucketResult>
      <Contents><Key>release/2026-02-01.0/theme=places/type=place/part-00001.parquet</Key></Contents>
      <Contents><Key>release/2026-02-01.0/theme=places/type=place/part-00000.parquet</Key></Contents>
    </ListBucketResult>
    """


def _workspace_temp_dir() -> Path:
    temp_dir = Path("tmp") / "test_overture_release_connector" / uuid4().hex
    temp_dir.mkdir(parents=True, exist_ok=False)
    return temp_dir


@pytest.mark.asyncio
async def test_fetch_downloads_latest_places_artifact_and_returns_deterministic_hash():
    temp_dir = _workspace_temp_dir()
    try:
        connector = OvertureReleaseConnector(cache_dir=str(temp_dir))
        expected_bytes = b"overture parquet bytes"
        expected_hash = hashlib.sha256(expected_bytes).hexdigest()

        connector._fetch_text = AsyncMock(
            side_effect=lambda url: _getting_data_html()
            if url == connector.getting_data_url
            else _places_listing_xml()
        )
        connector._fetch_bytes = AsyncMock(return_value=expected_bytes)

        payload = await connector.fetch("ignored query")

        assert payload == {
            "results": [
                {
                    "release": "2026-02-01.0",
                    "artifact_url": "https://overturemaps-us-west-2.s3.amazonaws.com/release/2026-02-01.0/theme=places/type=place/part-00000.parquet",
                    "file_path": str(temp_dir / "2026-02-01.0" / "part-00000.parquet"),
                    "file_hash": expected_hash,
                    "cached": False,
                }
            ]
        }
        assert (temp_dir / "2026-02-01.0" / "part-00000.parquet").read_bytes() == expected_bytes
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_fetch_uses_cached_artifact_without_redownloading():
    temp_dir = _workspace_temp_dir()
    try:
        connector = OvertureReleaseConnector(cache_dir=str(temp_dir))
        expected_bytes = b"overture parquet bytes"

        connector._fetch_text = AsyncMock(
            side_effect=lambda url: _getting_data_html()
            if url == connector.getting_data_url
            else _places_listing_xml()
        )
        connector._fetch_bytes = AsyncMock(return_value=expected_bytes)

        first_payload = await connector.fetch("ignored query")
        connector._fetch_bytes.reset_mock()
        second_payload = await connector.fetch("ignored query")

        connector._fetch_bytes.assert_not_awaited()
        assert first_payload["results"][0]["file_hash"] == second_payload["results"][0]["file_hash"]
        assert second_payload["results"][0]["cached"] is True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
