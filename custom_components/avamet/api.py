"""Bounded asynchronous transport using Home Assistant's shared HTTP session."""

from __future__ import annotations

import asyncio

import aiohttp

from .const import (
    DATA_URL,
    MAX_RESPONSE_BYTES,
    REQUEST_ATTEMPTS,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)
from .models import Observation
from .parser import ParseError, normalize_station_id, parse_observation


class AvametConnectionError(Exception):
    """A bounded request failed; messages do not expose response bodies."""


class AvametHTTPError(AvametConnectionError):
    def __init__(self, status: int, retry_after: int | None = None) -> None:
        super().__init__(f"AVAMET HTTP {status}")
        self.status = status
        self.retry_after = retry_after


class AvametClient:
    """One validated station; no session ownership, credentials or disk cache."""

    def __init__(self, session: aiohttp.ClientSession, station_id: str) -> None:
        self.session = session
        self.station_id = normalize_station_id(station_id)
        self.url = DATA_URL.format(station_id=self.station_id)

    async def async_get_observation(self) -> Observation:
        """Retry transient network failures once, never malformed HTML or 4xx."""
        for attempt in range(REQUEST_ATTEMPTS):
            try:
                html = await self._async_get_html()
            except AvametHTTPError as exc:
                if exc.status < 500 or attempt == REQUEST_ATTEMPTS - 1:
                    raise
            except (aiohttp.ClientError, TimeoutError) as exc:
                if attempt == REQUEST_ATTEMPTS - 1:
                    raise AvametConnectionError("Cannot connect to AVAMET") from exc
            else:
                # HTML parsing runs outside Home Assistant's event loop.
                return await asyncio.to_thread(parse_observation, html, self.station_id)
            await asyncio.sleep(1)
        raise AvametConnectionError("Cannot connect to AVAMET")

    async def _async_get_html(self) -> str:
        async with self.session.get(
            self.url,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
            allow_redirects=False,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "ca,es;q=0.9",
            },
        ) as response:
            if response.status != 200:
                retry = response.headers.get("Retry-After", "")
                retry_after = min(3600, max(300, int(retry))) if retry.isdigit() else None
                raise AvametHTTPError(response.status, retry_after)
            if response.content_type not in ("text/html", "application/xhtml+xml"):
                raise ParseError("unexpected_content_type")
            body = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ParseError("response_too_large")
            try:
                return body.decode(response.charset or "utf-8", errors="replace")
            except LookupError as exc:
                raise ParseError("unknown_response_encoding") from exc
