import os

from ipinfo.cache.default import DefaultCache
from ipinfo.details import Details
from ipinfo.handler_async import AsyncHandler
import pytest


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
    handler = AsyncHandler(token)
    headers = handler._get_headers()
    await handler.deinit()

    assert "user-agent" in headers
    assert "accept" in headers
    assert "authorization" in headers


@pytest.mark.parametrize("n", range(5))
@pytest.mark.asyncio
async def test_get_details(n):
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
    assert details.loc == "37.4056,-122.0775"
    assert details.latitude == "37.4056"
    assert details.longitude == "-122.0775"
    assert details.postal == "94043"
    assert details.timezone == "America/Los_Angeles"
    if token:
        asn = details.asn
        assert asn["asn"] == "AS15169"
        assert asn["name"] == "Google LLC"
        assert asn["domain"] == "google.com"
        assert asn["route"] == "8.8.8.0/24"
        assert asn["type"] == "business"

        company = details.company
        assert company["name"] == "Google LLC"
        assert company["domain"] == "google.com"
        assert company["type"] == "business"

        privacy = details.privacy
        assert privacy["vpn"] == False
        assert privacy["proxy"] == False
        assert privacy["tor"] == False
        assert privacy["hosting"] == False

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
        assert domains["total"] == 12988
        assert len(domains["domains"]) == 5

    await handler.deinit()


@pytest.mark.parametrize("n", range(5))
@pytest.mark.asyncio
async def test_get_batch_details(n):
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = AsyncHandler(token)
    ips = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
    details = await handler.getBatchDetails(ips)

    for ip in ips:
        assert ip in details
        d = details[ip]
        assert d["ip"] == ip
        if token:
            assert "asn" in d
            assert "company" in d
            assert "privacy" in d
            assert "abuse" in d
            assert "domains" in d

    await handler.deinit()
