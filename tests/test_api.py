"""Transport contract tests without third-party HTTP mock version coupling."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from custom_components.avamet.api import AvametClient, AvametConnectionError, AvametHTTPError
from custom_components.avamet.const import MAX_RESPONSE_BYTES
from custom_components.avamet.parser import ParseError


class Response:
    def __init__(self, body="", status=200, content_type="text/html", headers=None):
        self.body = body.encode()
        self.status = status
        self.content_type = content_type
        self.headers = headers or {}
        self.charset = "utf-8"
        self.content = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def iter_chunked(self, size):
        for index in range(0, len(self.body), size):
            yield self.body[index : index + size]


async def test_fetch(html):
    session = Mock(get=Mock(return_value=Response(html)))
    observation = await AvametClient(session, "c13m207e02").async_get_observation()
    assert observation.values["temperature_c"] == 30.1
    session.get.assert_called_once()
    kwargs = session.get.call_args.kwargs
    assert kwargs["allow_redirects"] is False
    assert kwargs["timeout"].total == 8
    assert session.get.call_args.args[0].endswith("id=c13m207e02")


async def test_retry_transient_failure(html):
    session = Mock(get=Mock(side_effect=[aiohttp.ClientConnectionError(), Response(html)]))
    with patch("custom_components.avamet.api.asyncio.sleep", new_callable=AsyncMock):
        result = await AvametClient(session, "c13m207e02").async_get_observation()
    assert result.values["temperature_c"] == 30.1
    assert session.get.call_count == 2


@pytest.mark.parametrize("exception", [aiohttp.ClientConnectionError(), TimeoutError()])
async def test_two_failures_are_bounded(exception):
    session = Mock(get=Mock(side_effect=exception))
    with patch("custom_components.avamet.api.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(AvametConnectionError):
            await AvametClient(session, "c13m207e02").async_get_observation()
    assert session.get.call_count == 2


async def test_server_error_retry(html):
    session = Mock(get=Mock(side_effect=[Response(status=503), Response(html)]))
    with patch("custom_components.avamet.api.asyncio.sleep", new_callable=AsyncMock):
        assert (
            await AvametClient(session, "c13m207e02").async_get_observation()
        ).station_id == "c13m207e02"
    assert session.get.call_count == 2


@pytest.mark.parametrize("status", [302, 403, 404, 429, 503])
async def test_http_failures(status):
    session = Mock(get=Mock(return_value=Response(status=status, headers={"Retry-After": "600"})))
    with patch("custom_components.avamet.api.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(AvametHTTPError) as error:
            await AvametClient(session, "c13m207e02").async_get_observation()
    assert error.value.status == status
    assert error.value.retry_after == 600
    assert session.get.call_count == (2 if status >= 500 else 1)


@pytest.mark.parametrize(
    "kind",
    ["malformed_html", "wrong_content_type", "response_limit", "unknown_encoding"],
)
async def test_invalid_body_not_retried(kind):
    response = Response("<html></html>")
    error = "missing_station_or_timestamp"
    if kind == "wrong_content_type":
        response.content_type = "application/json"
        error = "unexpected_content_type"
    elif kind == "response_limit":
        response.body = b"x" * (MAX_RESPONSE_BYTES + 1)
        error = "response_too_large"
    elif kind == "unknown_encoding":
        response.charset = "not-a-real-charset"
        error = "unknown_response_encoding"
    session = Mock(get=Mock(return_value=response))
    with pytest.raises(ParseError, match=error):
        await AvametClient(session, "c13m207e02").async_get_observation()
    assert session.get.call_count == 1


async def test_cancellation_is_not_swallowed():
    client = AvametClient(None, "c13m207e02")
    with patch.object(client, "_async_get_html", side_effect=asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            await client.async_get_observation()
