"""
Residential Proxy API client handler for fetching data from the IPinfo Residential Proxy service.
"""

import re
import time
from ipaddress import IPv4Address, IPv6Address

import requests

from . import handler_utils
from .bogon import is_bogon
from .cache.default import DefaultCache
from .details import Details
from .error import APIError
from .exceptions import RequestQuotaExceededError, TimeoutExceededError
from .handler_utils import (
    BATCH_MAX_SIZE,
    BATCH_REQ_TIMEOUT_DEFAULT,
    CACHE_MAXSIZE,
    CACHE_TTL,
    RESPROXY_API_URL,
    REQUEST_TIMEOUT_DEFAULT,
    cache_key,
)


class HandlerResProxy:
    """
    Allows client to request data for specified IP address using the ResProxy API.
    ResProxy API provides contextual data around Residential, Mobile, and
    Datacenter proxies.
    Instantiates and maintains access to cache.
    """

    def __init__(self, access_token=None, **kwargs):
        """
        Initialize the HandlerResProxy object with the cache initialized.
        """
        self.access_token = access_token

        # setup request options
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

        # set up custom headers
        self.headers = kwargs.get("headers", None)

    def getDetails(self, ip_address=None, timeout=None):
        """
        Get ResProxy details for the specified IP as a Details object.

        If `timeout` is not `None`, it will override the client-level timeout
        just for this operation.
        """
        # If the supplied IP address uses the object defined in the built-in
        # module ipaddress extract the appropriate string notation before
        # formatting the URL.
        if isinstance(ip_address, (IPv4Address, IPv6Address)):
            ip_address = ip_address.exploded

        # check if bogon.
        if ip_address and is_bogon(ip_address):
            details = {}
            details["ip"] = ip_address
            details["bogon"] = True
            return Details(details)

        # check cache first.
        try:
            cached_data = self.cache[cache_key(ip_address)]
            return Details(cached_data)
        except KeyError:
            pass

        # prepare request http options
        req_opts = {**self.request_options}
        if timeout is not None:
            req_opts["timeout"] = timeout

        # Build URL
        url = RESPROXY_API_URL
        if ip_address:
            url += "/" + ip_address

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

        # add cache
        self.cache[cache_key(ip_address)] = details

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
        Get ResProxy details for a batch of IP addresses at once.

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
        if batch_size is None:
            batch_size = BATCH_MAX_SIZE

        result = {}
        lookup_addresses = []

        # pre-populate with anything we've got in the cache, and keep around
        # the IPs not in the cache.
        for ip_address in ip_addresses:
            if isinstance(ip_address, (IPv4Address, IPv6Address)):
                ip_address = ip_address.exploded

            if ip_address and is_bogon(ip_address):
                details = {}
                details["ip"] = ip_address
                details["bogon"] = True
                result[ip_address] = Details(details)
            else:
                try:
                    cached_data = self.cache[cache_key(ip_address)]
                    result[ip_address] = Details(cached_data)
                except KeyError:
                    # prepend the url pattern for bulk lookup operations
                    lookup_addresses.append(f"resproxy/{ip_address}")

        if len(lookup_addresses) == 0:
            return result

        if timeout_total is not None:
            start_time = time.time()

        # prepare req options
        req_opts = {**self.request_options, "timeout": timeout_per_batch}

        # loop over batch chunks and do lookup for each.
        url = "https://api.ipinfo.io/batch"
        headers = handler_utils.get_headers(self.access_token, self.headers)
        headers["content-type"] = "application/json"

        for i in range(0, len(lookup_addresses), batch_size):
            # quit if total timeout is reached
            if timeout_total is not None and time.time() - start_time > timeout_total:
                return handler_utils.return_or_fail(
                    raise_on_fail, TimeoutExceededError(), result
                )

            chunk = lookup_addresses[i : i + batch_size]

            # lookup
            try:
                response = requests.post(url, json=chunk, headers=headers, **req_opts)
            except Exception as e:
                return handler_utils.return_or_fail(raise_on_fail, e, result)

            try:
                if response.status_code == 429:
                    raise RequestQuotaExceededError()
                response.raise_for_status()
            except Exception as e:
                return handler_utils.return_or_fail(raise_on_fail, e, result)

            json_response = response.json()

            for ip_address, data in json_response.items():
                unwound_ip_address = re.sub(r"^resproxy\/", "", ip_address)
                # Cache and format the data
                self.cache[cache_key(unwound_ip_address)] = data
                result[unwound_ip_address] = Details(data)

        return result
