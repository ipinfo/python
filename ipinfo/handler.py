import ipaddress
import json
import operator
import os
import requests
import sys
from .cache.default import DefaultCache
from .details import Details
from .exceptions import RequestQuotaExceededError


class Handler():
    """
    Allows client to request data for specified IP address. Instantiates and
    and maintains access to cache.
    """

    API_URL = 'https://ipinfo.io'
    CACHE_MAXSIZE = 4096
    CACHE_TTL = 60 * 60 * 24
    COUNTRY_FILE_DEFAULT = 'countries.json'

    def __init__(self, access_token=None, **kwargs):
        """Initialize the Handler object with country name list and the cache initialized."""
        self.access_token = access_token
        self.countries = self._read_country_names(kwargs.get('countries_file'))

        if 'cache' in kwargs:
            self.cache = kwargs['cache']
        else:
            cache_options = kwargs.get('cache_options', {})
            maxsize = cache_options.get('maxsize', self.CACHE_MAXSIZE)
            ttl = cache_options.get('ttl', self.CACHE_TTL)
            self.cache = DefaultCache(maxsize, ttl, **cache_options)

    def getDetails(self, ip_address=None):
        """Get details for specified IP address as a Details object."""
        raw_details = self._requestDetails(ip_address)
        raw_details['country_name'] = self.countries.get(raw_details.get('country'))
        raw_details['ip_address'] = ipaddress.ip_address(raw_details.get('ip'))

        lat, lon = None, None
        coords = tuple(raw_details.get('loc', '').split(','))
        if coords:
            lat, lon = coords[0], coords[1]
        raw_details['latitude'], raw_details['longitude'] = lat, lon

        return Details(raw_details)

    def _requestDetails(self, ip_address=None):
        """Get IP address data by sending request to IPinfo API."""
        if ip_address not in self.cache:
            url = self.API_URL
            if ip_address:
                url += '/' + ip_address

            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 429:
                raise RequestQuotaExceededError()
            response.raise_for_status()
            self.cache[ip_address] = response.json()

        return self.cache[ip_address]

    def _get_headers(self):
        """Built headers for request to IPinfo API."""
        headers = {
            'user-agent': 'IPinfoClient/Python{version}/1.0'.format(version=sys.version_info[0]),
            'accept': 'application/json'
        }

        if self.access_token:
            headers['authorization'] = 'Bearer {}'.format(self.access_token)

        return headers

    def _read_country_names(self, countries_file=None):
        """Read list of countries from specified country file or default file."""
        if not countries_file:
            countries_file = os.path.join(os.path.dirname(__file__), self.COUNTRY_FILE_DEFAULT)
        with open(countries_file) as f:
            countries_json = f.read()

        return json.loads(countries_json)
