"""
Main API client handler for fetching data from the IPinfo service.
"""

import json
import os
import sys

import requests

from .cache.default import DefaultCache
from .details import Details
from .exceptions import RequestQuotaExceededError


class Handler:
    """
    Allows client to request data for specified IP address. Instantiates and
    and maintains access to cache.
    """

    API_URL = "https://ipinfo.io"
    CACHE_MAXSIZE = 4096
    CACHE_TTL = 60 * 60 * 24
    COUNTRY_FILE_DEFAULT = "countries.json"
    REQUEST_TIMEOUT_DEFAULT = 2

    def __init__(self, access_token=None, **kwargs):
        """Initialize the Handler object with country name list and the cache initialized."""
        self.access_token = access_token
        self.countries = self._read_country_names(kwargs.get("countries_file"))
        self.request_options = kwargs.get("request_options", {})
        if "timeout" not in self.request_options:
            self.request_options["timeout"] = self.REQUEST_TIMEOUT_DEFAULT

        if "cache" in kwargs:
            self.cache = kwargs["cache"]
        else:
            cache_options = kwargs.get("cache_options", {})
            if "maxsize" not in cache_options:
                cache_options["maxsize"] = self.CACHE_MAXSIZE
            if "ttl" not in cache_options:
                cache_options["ttl"] = self.CACHE_TTL
            self.cache = DefaultCache(**cache_options)

    def getDetails(self, ip_address=None):
        """Get details for specified IP address as a Details object."""
        raw_details = self._requestDetails(ip_address)
        self._format_details(raw_details)
        return Details(raw_details)

    def getBatchDetails(self, ip_addresses):
        """Get details for a batch of IP addresses at once."""
        result = {}

        # Pre-populate with anything we've got in the cache, and keep around
        # the IPs not in the cache.
        lookup_addresses = []
        for ip_address in ip_addresses:
            if ip_address in self.cache:
                result[ip_address] = self.cache[ip_address]
            else:
                lookup_addresses.append(ip_address)

        # Do the lookup
        url = self.API_URL + "/batch"
        headers = self._get_headers()
        headers["content-type"] = "application/json"
        response = requests.post(
            url, json=lookup_addresses, headers=headers, **self.request_options
        )
        if response.status_code == 429:
            raise RequestQuotaExceededError()
        response.raise_for_status()

        # Fill up cache
        json_response = response.json()
        for ip_address, details in json_response.items():
            self.cache[ip_address] = details

        # Merge cached results with new lookup
        result.update(json_response)

        # Format every result
        for detail in result.values():
            if isinstance(detail, dict):
                self._format_details(detail)

        return result

    def _requestDetails(self, ip_address=None):
        """Get IP address data by sending request to IPinfo API."""
        if ip_address not in self.cache:
            url = self.API_URL
            if ip_address:
                url += "/" + ip_address

            response = requests.get(
                url, headers=self._get_headers(), **self.request_options
            )
            if response.status_code == 429:
                raise RequestQuotaExceededError()
            response.raise_for_status()
            self.cache[ip_address] = response.json()

        return self.cache[ip_address]

    def _get_headers(self):
        """Built headers for request to IPinfo API."""
        headers = {
            "user-agent": "IPinfoClient/Python{version}/2.0.0".format(
                version=sys.version_info[0]
            ),
            "accept": "application/json",
        }

        if self.access_token:
            headers["authorization"] = "Bearer {}".format(self.access_token)

        return headers

    def _format_details(self, details):
        details["country_name"] = self.countries.get(details.get("country"))
        details["latitude"], details["longitude"] = self._read_coords(
            details.get("loc")
        )

    def _read_coords(self, location):
        lat, lon = None, None
        coords = tuple(location.split(",")) if location else ""
        if len(coords) == 2 and coords[0] and coords[1]:
            lat, lon = coords[0], coords[1]
        return lat, lon

    def _read_country_names(self, countries_file=None):
        """Read list of countries from specified country file or default file."""
        if not countries_file:
            countries_file = os.path.join(
                os.path.dirname(__file__), self.COUNTRY_FILE_DEFAULT
            )
        with open(countries_file) as f:
            countries_json = f.read()

        return json.loads(countries_json)
