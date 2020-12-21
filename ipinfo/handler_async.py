"""
Main API client asynchronous handler for fetching data from the IPinfo service.
"""

from ipaddress import IPv4Address, IPv6Address
import asyncio
import json
import os
import sys

import aiohttp

from .cache.default import DefaultCache
from .details import Details
from .exceptions import RequestQuotaExceededError
from .handler_utils import (
    API_URL,
    COUNTRY_FILE_DEFAULT,
    BATCH_MAX_SIZE,
    CACHE_MAXSIZE,
    CACHE_TTL,
    REQUEST_TIMEOUT_DEFAULT,
    BATCH_REQ_TIMEOUT_DEFAULT,
)
from . import handler_utils


class AsyncHandler:
    """
    Allows client to request data for specified IP address asynchronously.
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

        # setup aiohttp
        self.httpsess = None

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

    async def init(self):
        """
        Initializes internal aiohttp connection pool.

        This isn't _required_, as the pool is initialized lazily when needed.
        But in case you require non-lazy initialization, you may await this.

        This is idempotent.
        """
        await self._ensure_aiohttp_ready()

    async def deinit(self):
        """
        Deinitialize the async handler.

        This is required in case you need to let go of the memory/state
        associated with the async handler in a long-running process.

        This is idempotent.
        """
        if self.httpsess:
            await self.httpsess.close()
            self.httpsess = None

    async def getDetails(self, ip_address=None):
        """Get details for specified IP address as a Details object."""
        self._ensure_aiohttp_ready()

        # If the supplied IP address uses the objects defined in the built-in
        # module ipaddress, extract the appropriate string notation before
        # formatting the URL.
        if isinstance(ip_address, IPv4Address) or isinstance(
            ip_address, IPv6Address
        ):
            ip_address = ip_address.exploded

        if ip_address in self.cache:
            return Details(self.cache[ip_address])

        # not in cache; do http req
        url = API_URL
        if ip_address:
            url += "/" + ip_address
        headers = handler_utils.get_headers(self.access_token)
        async with self.httpsess.get(url, headers=headers) as resp:
            if resp.status == 429:
                raise RequestQuotaExceededError()
            resp.raise_for_status()
            details = await resp.json()

        # format & cache
        handler_utils.format_details(details, self.countries)
        self.cache[ip_address] = details

        return Details(details)

    async def getBatchDetails(self, ip_addresses, batch_size=None):
        """
        Get details for a batch of IP addresses at once.

        There is no specified limit to the number of IPs this function can
        accept; it can handle as much as the user can fit in RAM (along with
        all of the response data, which is at least a magnitude larger than the
        input list).

        The input list is broken up into batches to abide by API requirements.
        The batch size can be adjusted with `batch_size` but is clipped to (and
        also defaults to) `BATCH_MAX_SIZE`.

        The concurrency level is currently unadjustable; coroutines will be
        created and consumed for all batches at once.
        """
        self._ensure_aiohttp_ready()

        if batch_size == None:
            batch_size = BATCH_MAX_SIZE

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

        # loop over batch chunks and prepare coroutines for each.
        reqs = []
        for i in range(0, len(ip_addresses), batch_size):
            chunk = ip_addresses[i : i + batch_size]

            # all in cache - return early.
            if len(lookup_addresses) == 0:
                return result

            # do http req
            url = API_URL + "/batch"
            headers = handler_utils.get_headers(self.access_token)
            headers["content-type"] = "application/json"
            reqs.append(
                self.httpsess.post(
                    url, data=json.dumps(lookup_addresses), headers=headers
                )
            )

        resps = await asyncio.gather(*reqs)
        for resp in resps:
            # gather data
            if resp.status == 429:
                raise RequestQuotaExceededError()
            resp.raise_for_status()
            json_resp = await resp.json()

            # format & fill up cache
            for ip_address, details in json_resp.items():
                if isinstance(details, dict):
                    handler_utils.format_details(details, self.countries)
                    self.cache[ip_address] = details

            # merge cached results with new lookup
            result.update(json_resp)

        return result

    def _ensure_aiohttp_ready(self):
        """Ensures aiohttp internal state is initialized."""
        if self.httpsess:
            return

        timeout = aiohttp.ClientTimeout(total=self.request_options["timeout"])
        self.httpsess = aiohttp.ClientSession(timeout=timeout)
