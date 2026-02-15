"""Live Overture release connector for downloading Places artifacts over HTTP."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from engine.ingestion.base import BaseConnector


class OvertureReleaseConnector(BaseConnector):
    """Resolve latest Overture release, download one Places parquet, and cache it."""

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        getting_data_url: str = "https://docs.overturemaps.org/getting-data/",
        blob_base_url: str = "https://overturemaps-us-west-2.s3.amazonaws.com",
        timeout_seconds: int = 30,
        max_artifact_size_bytes: int = 1024 * 1024 * 1024,
    ):
        self.cache_dir = Path(cache_dir or "engine/data/raw/overture_release")
        self.getting_data_url = getting_data_url
        self.blob_base_url = blob_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_artifact_size_bytes = max_artifact_size_bytes

    @property
    def source_name(self) -> str:
        return "overture_release"

    async def fetch(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        del query  # Connector fetch is release-driven rather than query-driven.

        release = await self._resolve_latest_release()
        artifacts = await self._resolve_places_artifacts(release)
        eligible_artifacts = [
            artifact for artifact in artifacts if artifact["size_bytes"] <= self.max_artifact_size_bytes
        ]
        if not eligible_artifacts:
            raise ValueError(
                f"No Overture places parquet artifact for release {release} satisfies size cap {self.max_artifact_size_bytes} bytes"
            )
        selected_artifact = eligible_artifacts[0]
        artifact_url = selected_artifact["url"]
        artifact_size_bytes = selected_artifact["size_bytes"]
        cache_path = self._artifact_cache_path(release, artifact_url)

        if cache_path.exists():
            file_bytes = cache_path.read_bytes()
        else:
            file_bytes = await self._fetch_bytes(artifact_url)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(file_bytes)
        rows = self._decode_place_rows(file_bytes, artifact_url)

        del release, artifact_size_bytes  # Selection metadata is internal; contract returns rows.
        return {"results": rows}

    def _artifact_cache_path(self, release: str, artifact_url: str) -> Path:
        artifact_name = artifact_url.rsplit("/", 1)[-1]
        return self.cache_dir / release / artifact_name

    async def _resolve_latest_release(self) -> str:
        html = await self._fetch_text(self.getting_data_url)
        release_ids = sorted(set(re.findall(r"release/(\d{4}-\d{2}-\d{2}\.\d+)/", html)))
        if not release_ids:
            raise ValueError("Could not resolve Overture release identifier from getting-data page")
        return release_ids[-1]

    async def _resolve_places_artifacts(self, release: str) -> List[Dict[str, Any]]:
        listing_xml = await self._fetch_text(self._places_listing_url(release))
        contents_blocks = re.findall(r"<Contents>(.*?)</Contents>", listing_xml, flags=re.DOTALL)
        key_pattern = (
            r"<Key>(release/"
            + re.escape(release)
            + r"/theme=places/type=place/[^<]+\.parquet)</Key>"
        )
        size_pattern = r"<Size>(\d+)</Size>"

        artifact_sizes: Dict[str, int] = {}
        for block in contents_blocks:
            key_match = re.search(key_pattern, block)
            size_match = re.search(size_pattern, block)
            if key_match is None or size_match is None:
                continue
            key = key_match.group(1)
            size_bytes = int(size_match.group(1))
            existing_size = artifact_sizes.get(key)
            if existing_size is None or size_bytes < existing_size:
                artifact_sizes[key] = size_bytes

        if not artifact_sizes:
            raise ValueError(f"Could not resolve Overture places parquet artifacts for release {release}")

        artifacts = [
            {"key": key, "url": f"{self.blob_base_url}/{key}", "size_bytes": size_bytes}
            for key, size_bytes in artifact_sizes.items()
        ]
        return sorted(artifacts, key=lambda artifact: (artifact["size_bytes"], artifact["key"]))

    def _places_listing_url(self, release: str) -> str:
        prefix = f"release/{release}/theme=places/type=place/"
        return f"{self.blob_base_url}?list-type=2&prefix={prefix}"

    async def _fetch_text(self, url: str) -> str:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)
        ) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status} while requesting {url}")
                return await response.text()

    async def _fetch_bytes(self, url: str) -> bytes:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)
        ) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status} while requesting {url}")
                return await response.read()

    def _decode_place_rows(
        self, artifact_bytes: bytes, artifact_url: str
    ) -> List[Dict[str, Any]]:
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError(
                "pyarrow is required to decode Overture parquet artifacts from "
                f"{artifact_url}"
            ) from exc

        try:
            table = pq.read_table(pa.BufferReader(artifact_bytes))
        except Exception as exc:
            raise RuntimeError(
                f"Failed decoding Overture parquet artifact {artifact_url}"
            ) from exc

        records = table.to_pylist()
        if not isinstance(records, list):
            raise ValueError(
                f"Decoded Overture artifact did not yield row records: {artifact_url}"
            )

        filtered_rows = [row for row in records if self._is_supported_place_row(row)]
        if not filtered_rows:
            raise ValueError(
                "Decoded Overture artifact contained no rows with required id and "
                f"name fields: {artifact_url}"
            )
        return filtered_rows

    def _is_supported_place_row(self, row: Any) -> bool:
        if not isinstance(row, dict):
            return False
        if row.get("id") is None:
            return False

        name = row.get("name")
        if isinstance(name, str) and name.strip():
            return True

        names = row.get("names")
        if isinstance(names, dict):
            primary_name = names.get("primary")
            if isinstance(primary_name, str) and primary_name.strip():
                return True
            if isinstance(primary_name, dict):
                value = primary_name.get("value")
                return isinstance(value, str) and bool(value.strip())

        return False

    async def save(self, data: dict, source_url: str) -> str:
        del data, source_url
        raise NotImplementedError(
            "OvertureReleaseConnector.save() is not used in orchestration adapter flow"
        )

    async def is_duplicate(self, content_hash: str) -> bool:
        del content_hash
        raise NotImplementedError(
            "OvertureReleaseConnector.is_duplicate() is not used in adapter flow"
        )
