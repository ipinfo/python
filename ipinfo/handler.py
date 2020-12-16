"""
Main API client handler for fetching data from the IPinfo service.
"""

from ipaddress import IPv4Address, IPv6Address
import json
import os
import sys

import requests

from .cache.default import DefaultCache
from .details import Details
from .exceptions import RequestQuotaExceededError
from . import handler_utils


class Handler:
    """
    Allows client to request data for specified IP address.
    Instantiates and maintains access to cache.
    """

    CACHE_MAXSIZE = 4096
    CACHE_TTL = 60 * 60 * 24
    REQUEST_TIMEOUT_DEFAULT = 2

    def __init__(self, access_token=None, **kwargs):
        """
        Initialize the Handler object with country name list and the
        cache initialized.
        """
        self.access_token = access_token

        # load countries file
        self.countries = handler_utils.read_country_names(
            kwargs.get("countries_file")
        )

        # setup req opts
        self.request_options = kwargs.get("request_options", {})
        if "timeout" not in self.request_options:
            self.request_options["timeout"] = self.REQUEST_TIMEOUT_DEFAULT

        # setup cache
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
        # If the supplied IP address uses the objects defined in the built-in
        # module ipaddress extract the appropriate string notation before
        # formatting the URL.
        if isinstance(ip_address, IPv4Address) or isinstance(
            ip_address, IPv6Address
        ):
            ip_address = ip_address.exploded

        if ip_address in self.cache:
            return Details(self.cache[ip_address])

        # not in cache; do http req
        url = handler_utils.API_URL
        if ip_address:
            url += "/" + ip_address
        headers = handler_utils.get_headers(self.access_token)
        response = requests.get(url, headers=headers, **self.request_options)
        if response.status_code == 429:
            raise RequestQuotaExceededError()
        response.raise_for_status()
        details = response.json()

        # format & cache
        handler_utils.format_details(details, self.countries)
        self.cache[ip_address] = details

        return Details(details)

    def getBatchDetails(self, ip_addresses):
        """Get details for a batch of IP addresses at once."""
        result = {}

        # Pre-populate with anything we've got in the cache, and keep around
        # the IPs not in the cache.
        lookup_addresses = []
        for ip_address in ip_addresses:
            # If the supplied IP address uses the objects defined in the
            # built-in module ipaddress extract the appropriate string notation
            # before formatting the URL.
            if isinstance(ip_address, IPv4Address) or isinstance(
                ip_address, IPv6Address
            ):
                ip_address = ip_address.exploded

            if ip_address in self.cache:
                result[ip_address] = self.cache[ip_address]
            else:
                lookup_addresses.append(ip_address)

        # Do the lookup
        url = handler_utils.API_URL + "/batch"
        headers = handler_utils.get_headers(self.access_token)
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
                handler_utils.format_details(detail, self.countries)

        return result
