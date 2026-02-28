import os

import pytest

from ipinfo import handler_utils
from ipinfo.cache.default import DefaultCache
from ipinfo.details import Details
from ipinfo.handler_resproxy import HandlerResProxy


def test_init():
    token = "mytesttoken"
    handler = HandlerResProxy(token)
    assert handler.access_token == token
    assert isinstance(handler.cache, DefaultCache)


def test_headers():
    token = "mytesttoken"
    handler = HandlerResProxy(token, headers={"custom_field": "yes"})
    headers = handler_utils.get_headers(token, handler.headers)

    assert "user-agent" in headers
    assert "accept" in headers
    assert "authorization" in headers
    assert "custom_field" in headers


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call ResProxy API without token",
)
def test_get_details():
    """Test basic ResProxy API lookup"""
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerResProxy(token)
    details = handler.getDetails("139.5.0.122")

    # Should return Details object
    assert isinstance(details, Details)
    assert details.ip == "139.5.0.122"

    # Check ResProxy-specific fields
    assert hasattr(details, "last_seen")
    assert hasattr(details, "percent_days_seen")
    assert hasattr(details, "service")


#############
# BOGON TESTS
#############


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call ResProxy API without token",
)
def test_bogon_details():
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerResProxy(token)
    details = handler.getDetails("127.0.0.1")
    assert isinstance(details, Details)
    assert details.all == {"bogon": True, "ip": "127.0.0.1"}


#####################
# BATCH TESTS
#####################


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call ResProxy API without token",
)
def test_batch_ips():
    """Test batch request with IPs"""
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerResProxy(token)
    results = handler.getBatchDetails(["139.5.0.122", "45.95.168.1"])

    assert len(results) == 2
    assert "139.5.0.122" in results
    assert "45.95.168.1" in results

    # Both should be Details objects
    assert isinstance(results["139.5.0.122"], Details)
    assert isinstance(results["45.95.168.1"], Details)

    # Check ResProxy-specific fields
    assert hasattr(results["139.5.0.122"], "last_seen")
    assert hasattr(results["139.5.0.122"], "percent_days_seen")
    assert hasattr(results["139.5.0.122"], "service")


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call ResProxy API without token",
)
def test_batch_with_bogon():
    """Test batch including bogon IPs"""
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerResProxy(token)
    results = handler.getBatchDetails(
        [
            "139.5.0.122",
            "127.0.0.1",  # Bogon
            "45.95.168.1",
        ]
    )

    assert len(results) == 3

    # Normal IPs should be Details
    assert isinstance(results["139.5.0.122"], Details)
    assert isinstance(results["45.95.168.1"], Details)

    # Bogon should also be Details with bogon flag
    assert isinstance(results["127.0.0.1"], Details)
    assert results["127.0.0.1"].bogon == True


#####################
# CACHING TESTS
#####################


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call ResProxy API without token",
)
def test_caching():
    """Test that results are properly cached"""
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerResProxy(token)

    # First request - should hit API
    details1 = handler.getDetails("139.5.0.122")
    assert isinstance(details1, Details)

    # Second request - should come from cache
    details2 = handler.getDetails("139.5.0.122")
    assert isinstance(details2, Details)
    assert details2.ip == details1.ip

    # Verify cache key exists
    cache_key_val = handler_utils.cache_key("139.5.0.122")
    assert cache_key_val in handler.cache


@pytest.mark.skipif(
    "IPINFO_TOKEN" not in os.environ,
    reason="Can't call ResProxy API without token",
)
def test_batch_caching():
    """Test that batch results are properly cached"""
    token = os.environ.get("IPINFO_TOKEN", "")
    handler = HandlerResProxy(token)

    # First batch request
    results1 = handler.getBatchDetails(["139.5.0.122", "45.95.168.1"])
    assert len(results1) == 2

    # Second batch with same IPs (should come from cache)
    results2 = handler.getBatchDetails(["139.5.0.122", "45.95.168.1"])
    assert len(results2) == 2
    assert results2["139.5.0.122"].ip == results1["139.5.0.122"].ip
