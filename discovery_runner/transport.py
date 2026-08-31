"""Small standard-library JSON transport for public HTTPS endpoints."""

from __future__ import annotations

import asyncio
import json
from urllib.request import Request, urlopen


class JsonTransport:
    async def json(self, method: str, url: str, payload=None):
        return await asyncio.to_thread(self._sync_json, method, url, payload)

    @staticmethod
    def _sync_json(method: str, url: str, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "OfficialJobDiscoveryRunner/0.1",
            },
        )
        with urlopen(request, timeout=30) as response:
            return json.load(response)

