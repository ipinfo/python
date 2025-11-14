import os

import pytest

from ipinfo import handler_utils
from ipinfo.cache.default import DefaultCache
from ipinfo.details import Details
from ipinfo.handler_plus import HandlerPlus


def test_init():
    token = "mytesttoken"
    handler = HandlerPlus(token)
    assert handler.access_token == token
    assert isinstance(handler.cache, DefaultCache)
    assert "US" in handler.countries


def test_headers():
    token = "mytesttoken"
    handler = HandlerPlus(token, headers={"custom_field": "yes"})
    headers = handler_utils.get_headers(token, handler.headers)

    assert "user-agent" in headers
    assert "accept" in headers
    assert "authorization" in headers
    assert "custom_field" in headers


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call Plus API without token",
)
def test_get_details():
    """Test basic Plus API lookup"""
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerPlus(token)
    details = handler.getDetails("8.8.8.8")

    # Should return Details object
    assert isinstance(details, Details)
    assert details.ip == "8.8.8.8"
    assert hasattr(details, "hostname")

    # Check nested geo object with all fields
    assert hasattr(details, "geo")
    assert isinstance(details.geo, dict)
    assert "city" in details.geo
    assert "region" in details.geo
    assert "region_code" in details.geo
    assert "country" in details.geo
    assert "country_code" in details.geo
    assert "continent" in details.geo
    assert "continent_code" in details.geo
    assert "latitude" in details.geo
    assert "longitude" in details.geo
    assert "timezone" in details.geo
    assert "postal_code" in details.geo
    assert "dma_code" in details.geo
    assert "geoname_id" in details.geo
    assert "radius" in details.geo

    # Check nested as object with all fields
    assert "as" in details.all
    as_obj = details.all["as"]
    assert isinstance(as_obj, dict)
    assert "asn" in as_obj
    assert "name" in as_obj
    assert "domain" in as_obj
    assert "type" in as_obj
    assert "last_changed" in as_obj

    # Check mobile and anonymous objects
    assert hasattr(details, "mobile")
    assert isinstance(details.mobile, dict)
    assert hasattr(details, "anonymous")
    assert isinstance(details.anonymous, dict)
    assert "is_proxy" in details.anonymous
    assert "is_relay" in details.anonymous
    assert "is_tor" in details.anonymous
    assert "is_vpn" in details.anonymous

    # Check all network/type flags
    assert hasattr(details, "is_anonymous")
    assert hasattr(details, "is_anycast")
    assert hasattr(details, "is_hosting")
    assert hasattr(details, "is_mobile")
    assert hasattr(details, "is_satellite")

    # Check geo formatting was applied
    assert "country_name" in details.geo
    assert "isEU" in details.geo
    assert "country_flag_url" in details.geo


#############
# BOGON TESTS
#############


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call Plus API without token",
)
def test_bogon_details():
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerPlus(token)
    details = handler.getDetails("127.0.0.1")
    assert isinstance(details, Details)
    assert details.all == {"bogon": True, "ip": "127.0.0.1"}


#####################
# BATCH TESTS
#####################


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call Plus API without token",
)
def test_batch_ips():
    """Test batch request with IPs"""
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerPlus(token)
    results = handler.getBatchDetails(["8.8.8.8", "1.1.1.1"])

    assert len(results) == 2
    assert "8.8.8.8" in results
    assert "1.1.1.1" in results

    # Both should be Details objects
    assert isinstance(results["8.8.8.8"], Details)
    assert isinstance(results["1.1.1.1"], Details)

    # Check structure - Plus API returns nested geo and as objects
    assert hasattr(results["8.8.8.8"], "geo")
    assert "as" in results["8.8.8.8"].all


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call Plus API without token",
)
def test_batch_with_bogon():
    """Test batch including bogon IPs"""
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerPlus(token)
    results = handler.getBatchDetails(
        [
            "8.8.8.8",
            "127.0.0.1",  # Bogon
            "1.1.1.1",
        ]
    )

    assert len(results) == 3

    # Normal IPs should be Details
    assert isinstance(results["8.8.8.8"], Details)
    assert isinstance(results["1.1.1.1"], Details)

    # Bogon should also be Details with bogon flag
    assert isinstance(results["127.0.0.1"], Details)
    assert results["127.0.0.1"].bogon == True


#####################
# CACHING TESTS
#####################


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call Plus API without token",
)
def test_caching():
    """Test that results are properly cached"""
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerPlus(token)

    # First request - should hit API
    details1 = handler.getDetails("8.8.8.8")
    assert isinstance(details1, Details)

    # Second request - should come from cache
    details2 = handler.getDetails("8.8.8.8")
    assert isinstance(details2, Details)
    assert details2.ip == details1.ip

    # Verify cache key exists
    cache_key_val = handler_utils.cache_key("8.8.8.8")
    assert cache_key_val in handler.cache


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call Plus API without token",
)
def test_batch_caching():
    """Test that batch results are properly cached"""
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerPlus(token)

    # First batch request
    results1 = handler.getBatchDetails(["8.8.8.8", "1.1.1.1"])
    assert len(results1) == 2

    # Second batch with same IPs (should come from cache)
    results2 = handler.getBatchDetails(["8.8.8.8", "1.1.1.1"])
    assert len(results2) == 2
    assert results2["8.8.8.8"].ip == results1["8.8.8.8"].ip
