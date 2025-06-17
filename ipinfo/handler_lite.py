"""
Main API client handler for fetching data from the IPinfo service.
"""

from ipaddress import IPv4Address, IPv6Address

import requests

from .error import APIError
from .cache.default import DefaultCache
from .details import Details
from .exceptions import RequestQuotaExceededError
from .handler_utils import (
    LITE_API_URL,
    CACHE_MAXSIZE,
    CACHE_TTL,
    REQUEST_TIMEOUT_DEFAULT,
    cache_key,
)
from . import handler_utils
from .bogon import is_bogon
from .data import (
    continents,
    countries,
    countries_currencies,
    eu_countries,
    countries_flags,
)


class HandlerLite:
    """
    Allows client to request data for specified IP address using the Lite API.
    Instantiates and maintains access to cache.
    """

    def __init__(self, access_token=None, **kwargs):
        """
        Initialize the Handler object with country name list and the
        cache initialized.
        """
        self.access_token = access_token

        # load countries file
        self.countries = kwargs.get("countries") or countries

        # load eu countries file
        self.eu_countries = kwargs.get("eu_countries") or eu_countries

        # load countries flags file
        self.countries_flags = kwargs.get("countries_flags") or countries_flags

        # load countries currency file
        self.countries_currencies = (
            kwargs.get("countries_currencies") or countries_currencies
        )

        # load continent file
        self.continents = kwargs.get("continent") or continents

        # setup req opts
        self.request_options = kwargs.get("request_options", {})
        if "timeout" not in self.request_options:
            self.request_options["timeout"] = REQUEST_TIMEOUT_DEFAULT

        # setup cache
        if "cache" in kwargs:
            self.cache = kwargs["cache"]
        else:
            cache_options = kwargs.get("cache_options", {})
            if "maxsize" not in cache_options:
                cache_options["maxsize"] = CACHE_MAXSIZE
            if "ttl" not in cache_options:
                cache_options["ttl"] = CACHE_TTL
            self.cache = DefaultCache(**cache_options)

        # setup custom headers
        self.headers = kwargs.get("headers", None)

    def getDetails(self, ip_address=None, timeout=None):
        """
        Get details for specified IP address as a Details object.

        If `timeout` is not `None`, it will override the client-level timeout
        just for this operation.
        """
        # If the supplied IP address uses the objects defined in the built-in
        # module ipaddress extract the appropriate string notation before
        # formatting the URL.
        if isinstance(ip_address, IPv4Address) or isinstance(ip_address, IPv6Address):
            ip_address = ip_address.exploded

        # check if bogon.
        if ip_address and is_bogon(ip_address):
            details = {}
            details["ip"] = ip_address
            details["bogon"] = True
            return Details(details)

        # check cache first.
        try:
            cached_ipaddr = self.cache[cache_key(ip_address)]
            return Details(cached_ipaddr)
        except KeyError:
            pass

        # prepare req http opts
        req_opts = {**self.request_options}
        if timeout is not None:
            req_opts["timeout"] = timeout

        # not in cache; do http req
        url = f"{LITE_API_URL}/{ip_address}" if ip_address else f"{LITE_API_URL}/me"
        headers = handler_utils.get_headers(self.access_token, self.headers)
        response = requests.get(url, headers=headers, **req_opts)
        if response.status_code == 429:
            raise RequestQuotaExceededError()
        if response.status_code >= 400:
            error_code = response.status_code
            content_type = response.headers.get("Content-Type")
            if content_type == "application/json":
                error_response = response.json()
            else:
                error_response = {"error": response.text}
            raise APIError(error_code, error_response)
        details = response.json()

        # format & cache
        handler_utils.format_details(
            details,
            self.countries,
            self.eu_countries,
            self.countries_flags,
            self.countries_currencies,
            self.continents,
        )
        self.cache[cache_key(ip_address)] = details

        return Details(details)
