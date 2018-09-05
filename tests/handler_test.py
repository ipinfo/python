from ipinfo_wrapper.cache.default import DefaultCache
from ipinfo_wrapper.details import Details
from ipinfo_wrapper.handler import Handler
import ipaddress


def test_init():
    token = 'mytesttoken'
    handler = Handler(token)
    assert handler.access_token == token
    assert isinstance(handler.cache, DefaultCache)
    assert 'US' in handler.countries


def test_headers():
    token = 'mytesttoken'
    handler = Handler(token)
    headers = handler._get_headers()

    assert 'user-agent' in headers
    assert 'accept' in headers
    assert 'authorization' in headers


def test_get_details():
    handler = Handler()
    fake_details = {
        'country': 'US',
        'ip': '127.0.0.1',
        'loc': '12.34,56.78'
    }

    handler._requestDetails = lambda x: fake_details

    details = handler.getDetails(fake_details['ip'])
    assert isinstance(details, Details)
    assert details.country == fake_details['country']
    assert details.country_name == 'United States'
    assert details.ip == fake_details['ip']
    assert isinstance(details.ip_address, ipaddress.IPv4Address)
    assert details.loc == fake_details['loc']
    assert details.longitude == '56.78'
    assert details.latitude == '12.34'
