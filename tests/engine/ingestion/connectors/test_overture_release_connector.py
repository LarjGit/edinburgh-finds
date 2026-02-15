from pathlib import Path
import shutil
from unittest.mock import AsyncMock, Mock
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
    return _places_listing_xml_from_items(
        [("part-00001.parquet", 200), ("part-00000.parquet", 100)]
    )


def _places_listing_xml_from_items(items) -> str:
    contents = "".join(
        (
            "<Contents>"
            f"<Key>release/2026-02-01.0/theme=places/type=place/{artifact_name}</Key>"
            f"<Size>{size_bytes}</Size>"
            "</Contents>"
        )
        for artifact_name, size_bytes in items
    )
    return f"<ListBucketResult>{contents}</ListBucketResult>"


def _overture_rows(name_suffix: str = "Row") -> list[dict]:
    return [
        {
            "id": f"08f2a3f1b87c9b1f03f0c1671dc1{name_suffix}000",
            "names": {"primary": f"Example {name_suffix} A"},
            "geometry": {"type": "Point", "coordinates": [-3.1902, 55.9521]},
        },
        {
            "id": f"08f2a3f1b87c9b1f03f0c1671dc1{name_suffix}001",
            "names": {"primary": f"Example {name_suffix} B"},
        },
    ]

def _workspace_temp_dir() -> Path:
    temp_dir = Path("tmp") / "test_overture_release_connector" / uuid4().hex
    temp_dir.mkdir(parents=True, exist_ok=False)
    return temp_dir


@pytest.mark.asyncio
async def test_fetch_downloads_latest_places_artifact_and_returns_row_records():
    temp_dir = _workspace_temp_dir()
    try:
        connector = OvertureReleaseConnector(cache_dir=str(temp_dir))
        expected_bytes = b"overture parquet bytes"
        expected_rows = _overture_rows("Download")

        connector._fetch_text = AsyncMock(
            side_effect=lambda url: _getting_data_html()
            if url == connector.getting_data_url
            else _places_listing_xml()
        )
        connector._fetch_bytes = AsyncMock(return_value=expected_bytes)
        connector._decode_place_rows = Mock(return_value=expected_rows)

        payload = await connector.fetch("ignored query")

        assert payload == {"results": expected_rows}
        connector._decode_place_rows.assert_called_once()
        decode_call = connector._decode_place_rows.call_args
        assert decode_call.args[0] == expected_bytes
        assert decode_call.args[1].endswith("part-00000.parquet")
        assert (temp_dir / "2026-02-01.0" / "part-00000.parquet").read_bytes() == expected_bytes
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_fetch_uses_cached_artifact_without_redownloading():
    temp_dir = _workspace_temp_dir()
    try:
        connector = OvertureReleaseConnector(cache_dir=str(temp_dir))
        expected_bytes = b"overture parquet bytes"
        expected_rows = _overture_rows("Cached")

        connector._fetch_text = AsyncMock(
            side_effect=lambda url: _getting_data_html()
            if url == connector.getting_data_url
            else _places_listing_xml()
        )
        connector._fetch_bytes = AsyncMock(return_value=expected_bytes)
        connector._decode_place_rows = Mock(return_value=expected_rows)

        first_payload = await connector.fetch("ignored query")
        connector._fetch_bytes.reset_mock()
        second_payload = await connector.fetch("ignored query")

        connector._fetch_bytes.assert_not_awaited()
        assert first_payload == {"results": expected_rows}
        assert second_payload == {"results": expected_rows}
        assert connector._decode_place_rows.call_count == 2
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.mark.asyncio
async def test_fetch_selects_smallest_eligible_artifact_with_deterministic_tie_break():
    temp_dir = _workspace_temp_dir()
    try:
        connector = OvertureReleaseConnector(cache_dir=str(temp_dir), max_artifact_size_bytes=800)
        connector._fetch_text = AsyncMock(
            side_effect=lambda url: _getting_data_html()
            if url == connector.getting_data_url
            else _places_listing_xml_from_items(
                [
                    ("part-00002.parquet", 700),
                    ("part-00000.parquet", 700),
                    ("part-00001.parquet", 900),
                ]
            )
        )
        connector._fetch_bytes = AsyncMock(return_value=b"overture parquet bytes")
        expected_rows = _overture_rows("TieBreak")
        connector._decode_place_rows = Mock(return_value=expected_rows)

        payload = await connector.fetch("ignored query")

        assert payload == {"results": expected_rows}
        decode_call = connector._decode_place_rows.call_args
        assert decode_call.args[1].endswith("part-00000.parquet")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.mark.asyncio
async def test_fetch_raises_when_no_artifact_satisfies_size_cap():
    connector = OvertureReleaseConnector(max_artifact_size_bytes=150)
    connector._fetch_text = AsyncMock(
        side_effect=lambda url: _getting_data_html()
        if url == connector.getting_data_url
        else _places_listing_xml_from_items(
            [("part-00000.parquet", 200), ("part-00001.parquet", 300)]
        )
    )
    connector._fetch_bytes = AsyncMock(return_value=b"unused")

    with pytest.raises(
        ValueError,
        match="No Overture places parquet artifact for release 2026-02-01.0 satisfies size cap 150 bytes",
    ):
        await connector.fetch("ignored query")
