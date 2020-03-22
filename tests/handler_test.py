from ipaddress import IPv4Address
import json

from ipinfo.cache.default import DefaultCache
from ipinfo.details import Details
from ipinfo.handler import Handler


def test_init():
    token = "mytesttoken"
    handler = Handler(token)
    assert handler.access_token == token
    assert isinstance(handler.cache, DefaultCache)
    assert "US" in handler.countries


def test_headers():
    token = "mytesttoken"
    handler = Handler(token)
    headers = handler._get_headers()

    assert "user-agent" in headers
    assert "accept" in headers
    assert "authorization" in headers


def test_get_details():
    handler = Handler()
    fake_details = {"country": "US", "ip": "127.0.0.1", "loc": "12.34,56.78"}

    handler._requestDetails = lambda x: fake_details

    details = handler.getDetails(fake_details["ip"])
    assert isinstance(details, Details)
    assert details.country == fake_details["country"]
    assert details.country_name == "United States"
    assert details.ip == fake_details["ip"]
    assert details.loc == fake_details["loc"]
    assert details.longitude == "56.78"
    assert details.latitude == "12.34"


def test_builtin_ip_types():
    handler = Handler()
    fake_details = {"country": "US", "ip": "127.0.0.1", "loc": "12.34,56.78"}

    handler._requestDetails = lambda x: fake_details

    details = handler.getDetails(IPv4Address(fake_details["ip"]))
    assert isinstance(details, Details)
    assert details.country == fake_details["country"]
    assert details.country_name == "United States"
    assert details.ip == fake_details["ip"]
    assert details.loc == fake_details["loc"]
    assert details.longitude == "56.78"
    assert details.latitude == "12.34"


def test_json_serialization():
    handler = Handler()
    fake_details = {
        "asn": {
            "asn": "AS20001",
            "domain": "twcable.com",
            "name": "Time Warner Cable Internet LLC",
            "route": "104.172.0.0/14",
            "type": "isp",
        },
        "city": "Los Angeles",
        "company": {
            "domain": "twcable.com",
            "name": "Time Warner Cable Internet LLC",
            "type": "isp",
        },
        "country": "US",
        "country_name": "United States",
        "hostname": "cpe-104-175-221-247.socal.res.rr.com",
        "ip": "104.175.221.247",
        "loc": "34.0293,-118.3570",
        "latitude": "34.0293",
        "longitude": "-118.3570",
        "phone": "323",
        "postal": "90016",
        "region": "California",
    }

    handler._requestDetails = lambda x: fake_details

    details = handler.getDetails(fake_details["ip"])
    assert isinstance(details, Details)
    assert json.dumps(details.all)
