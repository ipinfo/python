"""
Main API client asynchronous handler for fetching data from the IPinfo service.
"""

from ipaddress import IPv4Address, IPv6Address
import asyncio
import json
import time

import aiohttp

from .error import APIError
from .cache.default import DefaultCache
from .details import Details
from .exceptions import RequestQuotaExceededError, TimeoutExceededError
from .handler_utils import (
    API_URL,
    BATCH_MAX_SIZE,
    CACHE_MAXSIZE,
    CACHE_TTL,
    REQUEST_TIMEOUT_DEFAULT,
    BATCH_REQ_TIMEOUT_DEFAULT,
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

        # setup custom headers
        self.headers = kwargs.get("headers", None)

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

    async def getDetails(self, ip_address=None, timeout=None):
        """Get details for specified IP address as a Details object."""
        self._ensure_aiohttp_ready()

        # If the supplied IP address uses the objects defined in the built-in
        # module ipaddress, extract the appropriate string notation before
        # formatting the URL.
        if isinstance(ip_address, IPv4Address) or isinstance(
            ip_address, IPv6Address
        ):
            ip_address = ip_address.exploded

        # check if bogon.
        if ip_address and is_bogon(ip_address):
            details = {"ip": ip_address, "bogon": True}
            return Details(details)

        # check cache first.
        try:
            cached_ipaddr = self.cache[cache_key(ip_address)]
            return Details(cached_ipaddr)
        except KeyError:
            pass

        # not in cache; do http req
        url = API_URL
        if ip_address:
            url += "/" + ip_address
        headers = handler_utils.get_headers(self.access_token, self.headers)
        req_opts = {}
        if timeout is not None:
            req_opts["timeout"] = timeout
        async with self.httpsess.get(url, headers=headers, **req_opts) as resp:
            if resp.status == 429:
                raise RequestQuotaExceededError()
            if resp.status >= 400:
                error_response = await resp.json()
                error_code = resp.status
                raise APIError(error_code, error_response)
            details = await resp.json()

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

    async def getBatchDetails(
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

        The concurrency level is currently unadjustable; coroutines will be
        created and consumed for all batches at once.
        """
        self._ensure_aiohttp_ready()

        if batch_size is None:
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

            try:
                cached_ipaddr = self.cache[cache_key(ip_address)]
                result[ip_address] = cached_ipaddr
            except KeyError:
                lookup_addresses.append(ip_address)

        # all in cache - return early.
        if not lookup_addresses:
            return result

        # do start timer if necessary
        if timeout_total is not None:
            start_time = time.time()

        # loop over batch chunks and prepare coroutines for each.
        url = API_URL + "/batch"
        headers = handler_utils.get_headers(self.access_token, self.headers)
        headers["content-type"] = "application/json"

        # prepare coroutines that will make reqs and update results.
        reqs = [
            self._do_batch_req(
                lookup_addresses[i : i + batch_size],
                url,
                headers,
                timeout_per_batch,
                raise_on_fail,
                result,
            )
            for i in range(0, len(lookup_addresses), batch_size)
        ]

        try:
            _, pending = await asyncio.wait(
                {*reqs},
                timeout=timeout_total,
                return_when=asyncio.FIRST_EXCEPTION,
            )

            # if all done, return result.
            if not pending:
                return result

            # if some had a timeout, first cancel timed out stuff and wait for
            # cleanup. then exit with return_or_fail.
            for co in pending:
                try:
                    co.cancel()
                    await co
                except asyncio.CancelledError:
                    pass

            return handler_utils.return_or_fail(
                raise_on_fail, TimeoutExceededError(), result
            )
        except Exception as e:
            return handler_utils.return_or_fail(raise_on_fail, e, result)

        return result

    async def _do_batch_req(
        self, chunk, url, headers, timeout_per_batch, raise_on_fail, result
    ):
        """
        Coroutine which will do the actual POST request for getBatchDetails.
        """
        try:
            resp = await self.httpsess.post(
                url,
                data=json.dumps(chunk),
                headers=headers,
                timeout=timeout_per_batch,
            )
        except Exception as e:
            return handler_utils.return_or_fail(raise_on_fail, e, None)

        # gather data
        try:
            if resp.status == 429:
                raise RequestQuotaExceededError()
            resp.raise_for_status()
        except Exception as e:
            return handler_utils.return_or_fail(raise_on_fail, e, None)

        json_resp = await resp.json()

        # format & fill up cache
        for ip_address, details in json_resp.items():
            if isinstance(details, dict):
                handler_utils.format_details(
                    details,
                    self.countries,
                    self.eu_countries,
                    self.countries_flags,
                    self.countries_currencies,
                    self.continents,
                )
                self.cache[cache_key(ip_address)] = details

        # merge cached results with new lookup
        result.update(json_resp)

    def _ensure_aiohttp_ready(self):
        """Ensures aiohttp internal state is initialized."""
        if self.httpsess:
            return

        timeout = aiohttp.ClientTimeout(total=self.request_options["timeout"])
        self.httpsess = aiohttp.ClientSession(timeout=timeout)

    async def getBatchDetailsIter(
        self,
        ip_addresses,
        batch_size=None,
        raise_on_fail=True,
    ):
        if batch_size is None:
            batch_size = BATCH_MAX_SIZE

        results = {}
        lookup_addresses = []
        for ip_address in ip_addresses:
            if isinstance(ip_address, IPv4Address) or isinstance(
                ip_address, IPv6Address
            ):
                ip_address = ip_address.exploded

            if ip_address and is_bogon(ip_address):
                details = {"ip": ip_address, "bogon": True}
                yield Details(details)
            else:
                lookup_addresses.append(ip_address)

            try:
                cached_ipaddr = self.cache[cache_key(ip_address)]
                results[ip_address] = cached_ipaddr
            except KeyError:
                lookup_addresses.append(ip_address)

        if not lookup_addresses:
            yield results.items()

        url = API_URL + "/batch"
        headers = handler_utils.get_headers(self.access_token, self.headers)
        headers["content-type"] = "application/json"

        async def process_batch(batch):
            async with aiohttp.ClientSession(headers=headers) as session:
                response = await session.post(url, json=batch)
                response.raise_for_status()
                json_response = await response.json()
                for ip_address, details in json_response.items():
                    self.cache[cache_key(ip_address)] = details
                    results[ip_address] = details

        for i in range(0, len(lookup_addresses), batch_size):
            batch = lookup_addresses[i : i + batch_size]
            await process_batch(batch)

            for ip_address, details in results.items():
                if isinstance(details, dict):
                    handler_utils.format_details(
                        details,
                        self.countries,
                        self.eu_countries,
                        self.countries_flags,
                        self.countries_currencies,
                        self.continents,
                    )
                yield ip_address, details
