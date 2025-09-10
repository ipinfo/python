import json
import os

import aiohttp
import pytest

from ipinfo import handler_utils
from ipinfo.cache.default import DefaultCache
from ipinfo.details import Details
from ipinfo.error import APIError
from ipinfo.handler_lite_async import AsyncHandlerLite


class MockResponse:
    def __init__(self, text, status, headers):
        self._text = text
        self.status = status
        self.headers = headers

    def text(self):
        return self._text

    async def json(self):
        return json.loads(self._text)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aenter__(self):
        return self

    async def release(self):
        pass


@pytest.mark.asyncio
async def test_init():
    token = "mytesttoken"
    handler = AsyncHandlerLite(token)
    assert handler.access_token == token
    assert isinstance(handler.cache, DefaultCache)
    assert "PK" in handler.countries
    await handler.deinit()


@pytest.mark.asyncio
async def test_headers():
    token = "mytesttoken"
    handler = AsyncHandlerLite(token, headers={"custom_field": "yes"})
    headers = handler_utils.get_headers(token, handler.headers)
    await handler.deinit()

    assert "user-agent" in headers
    assert "accept" in headers
    assert "authorization" in headers
    assert "custom_field" in headers


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call Lite API without token",
)
@pytest.mark.asyncio
async def test_get_details():
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = AsyncHandlerLite(token)
    details = await handler.getDetails("8.8.8.8")
    assert isinstance(details, Details)
    assert details.ip == "8.8.8.8"
    assert details.asn == "AS15169"
    assert details.as_name == "Google LLC"
    assert details.as_domain == "google.com"
    assert details.country_code == "US"
    assert details.country == "United States"
    assert details.continent_code == "NA"
    assert details.continent == {"code": "NA", "name": "North America"}
    assert details.country_name == "United States"
    assert not details.isEU
    assert (
        details.country_flag_url
        == "https://cdn.ipinfo.io/static/images/countries-flags/US.svg"
    )
    assert details.country_flag == {"emoji": "🇺🇸", "unicode": "U+1F1FA U+1F1F8"}
    assert details.country_currency == {"code": "USD", "symbol": "$"}
    assert not hasattr(details, "latitude")
    assert not hasattr(details, "longitude")

    await handler.deinit()


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call Lite API without token",
)
@pytest.mark.parametrize(
    (
        "mock_resp_status_code",
        "mock_resp_headers",
        "mock_resp_error_msg",
        "expected_error_json",
    ),
    [
        pytest.param(
            503,
            {"Content-Type": "text/plain"},
            "Service Unavailable",
            {"error": "Service Unavailable"},
            id="5xx_not_json",
        ),
        pytest.param(
            403,
            {"Content-Type": "application/json"},
            '{"message": "missing token"}',
            {"message": "missing token"},
            id="4xx_json",
        ),
        pytest.param(
            400,
            {"Content-Type": "application/json"},
            '{"message": "missing field"}',
            {"message": "missing field"},
            id="400",
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_details_error(
    monkeypatch,
    mock_resp_status_code,
    mock_resp_headers,
    mock_resp_error_msg,
    expected_error_json,
):
    async def mock_get(*args, **kwargs):
        response = MockResponse(
            status=mock_resp_status_code,
            text=mock_resp_error_msg,
            headers=mock_resp_headers,
        )
        return response

    monkeypatch.setattr(
        aiohttp.ClientSession,
        "get",
        lambda *args, **kwargs: aiohttp.client._RequestContextManager(mock_get()),
    )
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = AsyncHandlerLite(token)
    with pytest.raises(APIError) as exc_info:
        await handler.getDetails("8.8.8.8")
    assert exc_info.value.error_code == mock_resp_status_code
    assert exc_info.value.error_json == expected_error_json


#############
# BOGON TESTS
#############


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call Lite API without token",
)
@pytest.mark.asyncio
async def test_bogon_details():
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = AsyncHandlerLite(token)
    details = await handler.getDetails("127.0.0.1")
    assert details.all == {"bogon": True, "ip": "127.0.0.1"}
