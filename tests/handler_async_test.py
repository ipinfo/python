import json
import os
import sys

import aiohttp
import pytest

import ipinfo
from ipinfo import handler_utils
from ipinfo.cache.default import DefaultCache
from ipinfo.details import Details
from ipinfo.error import APIError
from ipinfo.exceptions import RequestQuotaExceededError
from ipinfo.handler_async import AsyncHandler

skip_if_python_3_11_or_later = sys.version_info >= (3, 11)


class MockResponse:
    def __init__(self, text, status, headers):
        self._text = text
        self.status = status
        self.headers = headers

    async def text(self):
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
    handler = AsyncHandler(token)
    assert handler.access_token == token
    assert isinstance(handler.cache, DefaultCache)
    assert "PK" in handler.countries
    await handler.deinit()


@pytest.mark.asyncio
async def test_headers():
    token = "mytesttoken"
    handler = AsyncHandler(token, headers={"custom_field": "yes"})
    headers = handler_utils.get_headers(token, handler.headers)
    await handler.deinit()

    assert "user-agent" in headers
    assert "accept" in headers
    assert "authorization" in headers
    assert "custom_field" in headers


@pytest.mark.asyncio
async def test_get_details():
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = AsyncHandler(token)
    details = await handler.getDetails("8.8.8.8")
    assert isinstance(details, Details)
    assert details.ip == "8.8.8.8"
    assert details.hostname == "dns.google"
    assert details.city == "Mountain View"
    assert details.region == "California"
    assert details.country == "US"
    assert details.country_name == "United States"
    assert details.isEU == False
    country_flag = details.country_flag
    assert country_flag["emoji"] == "🇺🇸"
    assert country_flag["unicode"] == "U+1F1FA U+1F1F8"
    country_flag_url = details.country_flag_url
    assert (
        country_flag_url == "https://cdn.ipinfo.io/static/images/countries-flags/US.svg"
    )
    country_currency = details.country_currency
    assert country_currency["code"] == "USD"
    assert country_currency["symbol"] == "$"
    continent = details.continent
    assert continent["code"] == "NA"
    assert continent["name"] == "North America"
    assert details.loc is not None
    assert details.latitude is not None
    assert details.longitude is not None
    assert details.postal == "94043"
    assert details.timezone == "America/Los_Angeles"
    if token:
        asn = details.asn
        assert asn["asn"] == "AS15169"
        assert asn["name"] == "Google LLC"
        assert asn["domain"] == "google.com"
        assert asn["route"] == "8.8.8.0/24"
        assert asn["type"] == "hosting"

        company = details.company
        assert company["name"] == "Google LLC"
        assert company["domain"] == "google.com"
        assert company["type"] == "hosting"

        privacy = details.privacy
        assert privacy["vpn"] == False
        assert privacy["proxy"] == False
        assert privacy["tor"] == False
        assert privacy["relay"] == False
        assert privacy["hosting"] == True
        assert privacy["service"] == ""

        abuse = details.abuse
        assert (
            abuse["address"]
            == "US, CA, Mountain View, 1600 Amphitheatre Parkway, 94043"
        )
        assert abuse["country"] == "US"
        assert abuse["email"] == "network-abuse@google.com"
        assert abuse["name"] == "Abuse"
        assert abuse["network"] == "8.8.8.0/24"
        assert abuse["phone"] == "+1-650-253-0000"

        domains = details.domains
        assert domains["ip"] == "8.8.8.8"
        # NOTE: actual number changes too much
        assert "total" in domains
        assert len(domains["domains"]) == 5

    await handler.deinit()


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
    handler = AsyncHandler(token)
    with pytest.raises(APIError) as exc_info:
        await handler.getDetails("8.8.8.8")
    assert exc_info.value.error_code == mock_resp_status_code
    assert exc_info.value.error_json == expected_error_json


@pytest.mark.asyncio
async def test_get_details_quota_error(monkeypatch):
    async def mock_get(*args, **kwargs):
        response = MockResponse(status=429, text="Quota exceeded", headers={})
        return response

    monkeypatch.setattr(
        aiohttp.ClientSession,
        "get",
        lambda *args, **kwargs: aiohttp.client._RequestContextManager(mock_get()),
    )
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = AsyncHandler(token)
    with pytest.raises(RequestQuotaExceededError):
        await handler.getDetails("8.8.8.8")


#############
# BATCH TESTS
#############

_batch_ip_addrs = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]


def _prepare_batch_test():
    """Helper for preparing batch test cases."""
    token = os.environ.get("IPINFO_TOKEN", "")
    if not token:
        pytest.skip("token required for batch tests")
    handler = AsyncHandler(token)
    return handler, token, _batch_ip_addrs


def _check_batch_details(ips, details, token):
    """Helper for batch tests."""
    for ip in ips:
        assert ip in details
        d = details[ip]
        assert d["ip"] == ip
        assert "country" in d
        assert "country_name" in d
        if token:
            assert "asn" in d
            assert "company" in d
            assert "privacy" in d
            assert "abuse" in d
            assert "domains" in d


@pytest.mark.skipif(
    skip_if_python_3_11_or_later, reason="Requires Python 3.10 or earlier"
)
@pytest.mark.parametrize("batch_size", [None, 1, 2, 3])
@pytest.mark.asyncio
async def test_get_batch_details(batch_size):
    handler, token, ips = _prepare_batch_test()
    details = await handler.getBatchDetails(ips, batch_size=batch_size)
    _check_batch_details(ips, details, token)
    await handler.deinit()


def _check_iterative_batch_details(ip, details, token):
    """Helper for iterative batch tests."""
    assert ip == details.get("ip")
    assert "country" in details
    assert "city" in details
    if token:
        assert "asn" in details or "anycast" in details
        assert "company" in details or "org" in details
        assert "privacy" in details or "anycast" in details
        assert "abuse" in details or "anycast" in details
        assert "domains" in details or "anycast" in details


@pytest.mark.parametrize("batch_size", [None, 1, 2, 3])
@pytest.mark.asyncio
async def test_get_iterative_batch_details(batch_size):
    handler, token, ips = _prepare_batch_test()
    async for ips, details in handler.getBatchDetailsIter(ips, batch_size):
        _check_iterative_batch_details(ips, details, token)


@pytest.mark.skipif(
    skip_if_python_3_11_or_later, reason="Requires Python 3.10 or earlier"
)
@pytest.mark.parametrize("batch_size", [None, 1, 2, 3])
@pytest.mark.asyncio
async def test_get_batch_details_total_timeout(batch_size):
    handler, token, ips = _prepare_batch_test()
    with pytest.raises(ipinfo.exceptions.TimeoutExceededError):
        await handler.getBatchDetails(ips, batch_size=batch_size, timeout_total=0.001)
    await handler.deinit()


#############
# BOGON TESTS
#############


@pytest.mark.asyncio
async def test_bogon_details():
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = AsyncHandler(token)
    details = await handler.getDetails("127.0.0.1")
    assert details.all == {"bogon": True, "ip": "127.0.0.1"}


#################
# RESPROXY TESTS
#################


@pytest.mark.asyncio
async def test_get_resproxy(monkeypatch):
    mock_response = MockResponse(
        json.dumps(
            {
                "ip": "175.107.211.204",
                "last_seen": "2025-01-20",
                "percent_days_seen": 0.85,
                "service": "example_service",
            }
        ),
        200,
        {"Content-Type": "application/json"},
    )

    def mock_get(*args, **kwargs):
        return mock_response

    handler = AsyncHandler("test_token")
    handler._ensure_aiohttp_ready()
    monkeypatch.setattr(handler.httpsess, "get", mock_get)

    details = await handler.getResproxy("175.107.211.204")
    assert isinstance(details, Details)
    assert details.ip == "175.107.211.204"
    assert details.last_seen == "2025-01-20"
    assert details.percent_days_seen == 0.85
    assert details.service == "example_service"
    await handler.deinit()


@pytest.mark.asyncio
async def test_get_resproxy_caching(monkeypatch):
    call_count = 0

    def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return MockResponse(
            json.dumps(
                {
                    "ip": "175.107.211.204",
                    "last_seen": "2025-01-20",
                    "percent_days_seen": 0.85,
                    "service": "example_service",
                }
            ),
            200,
            {"Content-Type": "application/json"},
        )

    handler = AsyncHandler("test_token")
    handler._ensure_aiohttp_ready()
    monkeypatch.setattr(handler.httpsess, "get", mock_get)

    # First call should hit the API
    details1 = await handler.getResproxy("175.107.211.204")
    # Second call should hit the cache
    details2 = await handler.getResproxy("175.107.211.204")
    assert details1.ip == details2.ip
    # Verify only one API call was made (second was cached)
    assert call_count == 1
    await handler.deinit()


class MockBatchResponse(MockResponse):
    """MockResponse with raise_for_status for batch endpoint mocking."""

    def raise_for_status(self):
        if self.status >= 400:
            raise Exception(f"HTTP {self.status}")


@pytest.mark.asyncio
async def test_get_batch_details_with_resproxy(monkeypatch):
    """Prefixed lookups like 'resproxy/IP' should not crash in async getBatchDetails."""
    mock_api_response = {
        "resproxy/1.2.3.4": {"ip": "1.2.3.4", "service": "example"},
        "8.8.8.8": {"ip": "8.8.8.8", "country": "US"},
    }

    async def mock_post(*args, **kwargs):
        return MockBatchResponse(
            json.dumps(mock_api_response),
            200,
            {"Content-Type": "application/json"},
        )

    handler = AsyncHandler("test_token")
    handler._ensure_aiohttp_ready()
    monkeypatch.setattr(handler.httpsess, "post", mock_post)
    result = await handler.getBatchDetails(["resproxy/1.2.3.4", "8.8.8.8"])
    assert "resproxy/1.2.3.4" in result
    assert "8.8.8.8" in result
    await handler.deinit()


@pytest.mark.asyncio
async def test_get_batch_details_mixed_resproxy_and_bogon(monkeypatch):
    """Async getBatchDetails: mixing prefixed, plain, and bogon IPs."""
    mock_api_response = {
        "resproxy/1.2.3.4": {"ip": "1.2.3.4", "service": "ex"},
        "8.8.8.8": {"ip": "8.8.8.8", "country": "US"},
    }

    async def mock_post(*args, **kwargs):
        return MockBatchResponse(
            json.dumps(mock_api_response),
            200,
            {"Content-Type": "application/json"},
        )

    handler = AsyncHandler("test_token")
    handler._ensure_aiohttp_ready()
    monkeypatch.setattr(handler.httpsess, "post", mock_post)
    result = await handler.getBatchDetails(["resproxy/1.2.3.4", "8.8.8.8", "127.0.0.1"])
    assert "resproxy/1.2.3.4" in result
    assert "8.8.8.8" in result
    await handler.deinit()
