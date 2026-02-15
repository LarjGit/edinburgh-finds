"""Live Overture release connector for downloading Places artifacts over HTTP."""

import hashlib
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
    ):
        self.cache_dir = Path(cache_dir or "engine/data/raw/overture_release")
        self.getting_data_url = getting_data_url
        self.blob_base_url = blob_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def source_name(self) -> str:
        return "overture_release"

    async def fetch(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        del query  # Connector fetch is release-driven rather than query-driven.

        release = await self._resolve_latest_release()
        artifact_url = (await self._resolve_places_artifact_urls(release))[0]
        cache_path = self._artifact_cache_path(release, artifact_url)

        if cache_path.exists():
            file_bytes = cache_path.read_bytes()
            cached = True
        else:
            file_bytes = await self._fetch_bytes(artifact_url)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(file_bytes)
            cached = False

        return {
            "results": [
                {
                    "release": release,
                    "artifact_url": artifact_url,
                    "file_path": str(cache_path),
                    "file_hash": hashlib.sha256(file_bytes).hexdigest(),
                    "cached": cached,
                }
            ]
        }

    def _artifact_cache_path(self, release: str, artifact_url: str) -> Path:
        artifact_name = artifact_url.rsplit("/", 1)[-1]
        return self.cache_dir / release / artifact_name

    async def _resolve_latest_release(self) -> str:
        html = await self._fetch_text(self.getting_data_url)
        release_ids = sorted(set(re.findall(r"release/(\d{4}-\d{2}-\d{2}\.\d+)/", html)))
        if not release_ids:
            raise ValueError("Could not resolve Overture release identifier from getting-data page")
        return release_ids[-1]

    async def _resolve_places_artifact_urls(self, release: str) -> List[str]:
        listing_xml = await self._fetch_text(self._places_listing_url(release))
        key_pattern = (
            r"<Key>(release/"
            + re.escape(release)
            + r"/theme=places/type=place/[^<]+\.parquet)</Key>"
        )
        keys = sorted(set(re.findall(key_pattern, listing_xml)))
        if not keys:
            raise ValueError(f"Could not resolve Overture places parquet artifacts for release {release}")
        return [f"{self.blob_base_url}/{key}" for key in keys]

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
