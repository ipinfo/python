import os

import pytest
from ipinfo import handler_utils
from ipinfo.cache.default import DefaultCache
from ipinfo.details import Details
from ipinfo.handler_lite import HandlerLite


def test_init():
    token = "mytesttoken"
    handler = HandlerLite(token)
    assert handler.access_token == token
    assert isinstance(handler.cache, DefaultCache)
    assert "US" in handler.countries


def test_headers():
    token = "mytesttoken"
    handler = HandlerLite(token, headers={"custom_field": "yes"})
    headers = handler_utils.get_headers(token, handler.headers)

    assert "user-agent" in headers
    assert "accept" in headers
    assert "authorization" in headers
    assert "custom_field" in headers


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call Lite API without token",
)
def test_get_details():
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerLite(token)
    details = handler.getDetails("8.8.8.8")
    assert isinstance(details, Details)
    assert details.ip == "8.8.8.8"
    assert details.asn == "AS15169"
    assert details.as_name == "Google LLC"
    assert details.as_domain == "google.com"
    assert details.country_code == "US"
    assert details.country == "United States"
    assert details.continent_code == "NA"
    assert details.continent is None
    assert details.country_name is None
    assert not details.isEU
    assert (
        details.country_flag_url
        == "https://cdn.ipinfo.io/static/images/countries-flags/United States.svg"
    )
    assert details.country_flag is None
    assert details.country_currency is None
    assert details.latitude is None
    assert details.longitude is None


#############
# BOGON TESTS
#############


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call Lite API without token",
)
def test_bogon_details():
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerLite(token)
    details = handler.getDetails("127.0.0.1")
    assert isinstance(details, Details)
    assert details.all == {"bogon": True, "ip": "127.0.0.1"}
