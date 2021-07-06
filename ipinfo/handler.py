"""
Main API client handler for fetching data from the IPinfo service.
"""

from ipaddress import IPv4Address, IPv6Address
import json
import os
import sys
import time

import requests

from .cache.default import DefaultCache
from .details import Details
from .exceptions import RequestQuotaExceededError, TimeoutExceededError
from .handler_utils import (
    API_URL,
    COUNTRY_FILE_DEFAULT,
    BATCH_MAX_SIZE,
    CACHE_MAXSIZE,
    CACHE_TTL,
    REQUEST_TIMEOUT_DEFAULT,
    BATCH_REQ_TIMEOUT_DEFAULT,
    cache_key,
)
from . import handler_utils


class Handler:
    """
    Allows client to request data for specified IP address.
    Instantiates and maintains access to cache.
    """

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

    def getDetails(self, ip_address=None, timeout=None):
        """
        Get details for specified IP address as a Details object.

        If `timeout` is not `None`, it will override the client-level timeout
        just for this operation.
        """
        # If the supplied IP address uses the objects defined in the built-in
        # module ipaddress extract the appropriate string notation before
        # formatting the URL.
        if isinstance(ip_address, IPv4Address) or isinstance(
            ip_address, IPv6Address
        ):
            ip_address = ip_address.exploded

        # check cache first.
        try:
            cached_ipaddr = self.cache[cache_key(ip_address)]
            cached_ipaddr["cached"] = True
            return Details(cached_ipaddr)
        except KeyError:
            pass

        # prepare req http opts
        req_opts = {**self.request_options}
        if timeout is not None:
            req_opts["timeout"] = timeout

        # not in cache; do http req
        url = API_URL
        if ip_address:
            url += "/" + ip_address
        headers = handler_utils.get_headers(self.access_token)
        response = requests.get(url, headers=headers, **req_opts)
        if response.status_code == 429:
            raise RequestQuotaExceededError()
        response.raise_for_status()
        details = response.json()

        # format & cache
        handler_utils.format_details(details, self.countries)
        self.cache[cache_key(ip_address)] = details
        details["cached"] = False
        return Details(details)

    def getBatchDetails(
        self,
        ip_addresses,
        batch_size=None,
        timeout_per_batch=BATCH_REQ_TIMEOUT_DEFAULT,
        timeout_total=None,
        raise_on_fail=True,
    ):
        """
        Get details for a batch of IP addresses at once.

        There is no specified limit to the number of IPs this function can
        accept; it can handle as much as the user can fit in RAM (along with
        all of the response data, which is at least a magnitude larger than the
        input list).

        The input list is broken up into batches to abide by API requirements.
        The batch size can be adjusted with `batch_size` but is clipped to
        `BATCH_MAX_SIZE`.
        Defaults to `BATCH_MAX_SIZE`.

        For each batch, `timeout_per_batch` indicates the maximum seconds to
        spend waiting for the HTTP request to complete. If any batch fails with
        this timeout, the whole operation fails.
        Defaults to `BATCH_REQ_TIMEOUT_DEFAULT` seconds.

        `timeout_total` is a seconds-denominated hard-timeout for the time
        spent in HTTP operations; regardless of whether all batches have
        succeeded so far, if `timeout_total` is reached, the whole operation
        will fail by raising `TimeoutExceededError`.
        Defaults to being turned off.

        `raise_on_fail`, if turned off, will return any result retrieved so far
        rather than raise an exception when errors occur, including timeout and
        quota errors.
        Defaults to on.
        """
        if batch_size == None:
            batch_size = BATCH_MAX_SIZE

        result = {}

        # pre-populate with anything we've got in the cache, and keep around
        # the IPs not in the cache.
        lookup_addresses = []
        for ip_address in ip_addresses:
            # if the supplied IP address uses the objects defined in the
            # built-in module ipaddress extract the appropriate string notation
            # before formatting the URL.
            if isinstance(ip_address, IPv4Address) or isinstance(
                ip_address, IPv6Address
            ):
                ip_address = ip_address.exploded

            try:
                cached_ipaddr = self.cache[cache_key(ip_address)]
                cached_ipaddr["cached"] = True
                result[ip_address] = cached_ipaddr
            except KeyError:
                lookup_addresses.append(ip_address)

        # all in cache - return early.
        if len(lookup_addresses) == 0:
            return result

        # do start timer if necessary
        if timeout_total is not None:
            start_time = time.time()

        # prepare req http options
        req_opts = {**self.request_options, "timeout": timeout_per_batch}

        # loop over batch chunks and do lookup for each.
        url = API_URL + "/batch"
        headers = handler_utils.get_headers(self.access_token)
        headers["content-type"] = "application/json"
        for i in range(0, len(lookup_addresses), batch_size):
            # quit if total timeout is reached.
            if (
                timeout_total is not None
                and time.time() - start_time > timeout_total
            ):
                return handler_utils.return_or_fail(
                    raise_on_fail, TimeoutExceededError(), result
                )

            chunk = lookup_addresses[i : i + batch_size]

            # lookup
            response = requests.post(
                url, json=chunk, headers=headers, **req_opts
            )

            # fail on bad status codes
            try:
                if response.status_code == 429:
                    raise RequestQuotaExceededError()
                response.raise_for_status()
            except Exception as e:
                return handler_utils.return_or_fail(raise_on_fail, e, result)

            # fill cache
            json_response = response.json()
            for ip_address, details in json_response.items():
                self.cache[cache_key(ip_address)] = details
                details["cached"] = False

            # merge cached results with new lookup
            result.update(json_response)

            # format all
            for detail in result.values():
                if isinstance(detail, dict):
                    handler_utils.format_details(detail, self.countries)

        return result

    def getMap(self, ips):
        """
        Gets a URL to a map on https://ipinfo.io/map given a list of IPs (max
        500,000).
        """
        ip_strs = []
        for ip in ips:
            # if the supplied IP address uses the objects defined in the
            # built-in module ipaddress extract the appropriate string notation
            # before formatting the URL.
            if isinstance(ip, IPv4Address) or isinstance(ip, IPv6Address):
                ip = ip.exploded

            ip_strs.append(ip)

        req_opts = {**self.request_options}
        url = f"{API_URL}/map?cli=1"
        headers = handler_utils.get_headers(None)
        headers["content-type"] = "application/json"
        response = requests.post(
            url, json=ip_strs, headers=headers, **req_opts
        )
        response.raise_for_status()
        return response.json()["reportUrl"]
