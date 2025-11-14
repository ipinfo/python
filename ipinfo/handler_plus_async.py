"""
Plus API client asynchronous handler for fetching data from the IPinfo Plus service.
"""

import asyncio
import json
from ipaddress import IPv4Address, IPv6Address

import aiohttp

from . import handler_utils
from .bogon import is_bogon
from .cache.default import DefaultCache
from .data import (
    continents,
    countries,
    countries_currencies,
    countries_flags,
    eu_countries,
)
from .details import Details
from .error import APIError
from .exceptions import RequestQuotaExceededError, TimeoutExceededError
from .handler_utils import (
    BATCH_MAX_SIZE,
    BATCH_REQ_TIMEOUT_DEFAULT,
    CACHE_MAXSIZE,
    CACHE_TTL,
    PLUS_API_URL,
    REQUEST_TIMEOUT_DEFAULT,
    cache_key,
)


class AsyncHandlerPlus:
    """
    Allows client to request data for specified IP address asynchronously using the Plus API.
    Plus API provides city-level geolocation with nested geo and AS objects.
    Instantiates and maintains access to cache.
    """

    def __init__(self, access_token=None, **kwargs):
        """
        Initialize the AsyncHandlerPlus object with country name list and the
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
        """
        Get Plus details for specified IP address as a Details object.

        If `timeout` is not `None`, it will override the client-level timeout
        just for this operation.
        """
        self._ensure_aiohttp_ready()

        # If the supplied IP address uses the objects defined in the built-in
        # module ipaddress, extract the appropriate string notation before
        # formatting the URL.
        if isinstance(ip_address, IPv4Address) or isinstance(ip_address, IPv6Address):
            ip_address = ip_address.exploded

        # check if bogon.
        if ip_address and is_bogon(ip_address):
            details = {"ip": ip_address, "bogon": True}
            return Details(details)

        # check cache first.
        try:
            cached_data = self.cache[cache_key(ip_address)]
            return Details(cached_data)
        except KeyError:
            pass

        # not in cache; do http req
        url = PLUS_API_URL
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
                error_code = resp.status
                content_type = resp.headers.get("Content-Type")
                if content_type == "application/json":
                    error_response = await resp.json()
                else:
                    error_response = {"error": resp.text()}
                raise APIError(error_code, error_response)
            details = await resp.json()

        # format & cache
        self._format_plus_details(details)
        self.cache[cache_key(ip_address)] = details

        return Details(details)

    def _format_plus_details(self, details):
        """
        Format Plus response details.
        Plus has nested geo and as objects that need special formatting.
        """
        # Format geo object if present
        if "geo" in details and details["geo"]:
            geo = details["geo"]
            if "country_code" in geo:
                country_code = geo["country_code"]
                geo["country_name"] = self.countries.get(country_code)
                geo["isEU"] = country_code in self.eu_countries
                geo["country_flag"] = self.countries_flags.get(country_code)
                geo["country_currency"] = self.countries_currencies.get(country_code)
                geo["continent"] = self.continents.get(country_code)
                geo["country_flag_url"] = (
                    f"{handler_utils.COUNTRY_FLAGS_URL}{country_code}.svg"
                )

        # Top-level country_code might also exist in some responses
        if "country_code" in details:
            country_code = details["country_code"]
            details["country_name"] = self.countries.get(country_code)
            details["isEU"] = country_code in self.eu_countries
            details["country_flag"] = self.countries_flags.get(country_code)
            details["country_currency"] = self.countries_currencies.get(country_code)
            details["continent"] = self.continents.get(country_code)
            details["country_flag_url"] = (
                f"{handler_utils.COUNTRY_FLAGS_URL}{country_code}.svg"
            )

    async def getBatchDetails(
        self,
        ip_addresses,
        batch_size=None,
        timeout_per_batch=BATCH_REQ_TIMEOUT_DEFAULT,
        timeout_total=None,
        raise_on_fail=True,
    ):
        """
        Get Plus details for a batch of IP addresses at once.

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
                    lookup_addresses.append(ip_address)

        # all in cache - return early.
        if not lookup_addresses:
            return result

        # loop over batch chunks and prepare coroutines for each.
        url = "https://api.ipinfo.io/batch"
        headers = handler_utils.get_headers(self.access_token, self.headers)
        headers["content-type"] = "application/json"

        # prepare tasks that will make reqs and update results.
        tasks = [
            asyncio.create_task(
                self._do_batch_req(
                    lookup_addresses[i : i + batch_size],
                    url,
                    headers,
                    timeout_per_batch,
                    raise_on_fail,
                    result,
                )
            )
            for i in range(0, len(lookup_addresses), batch_size)
        ]

        try:
            _, pending = await asyncio.wait(
                tasks,
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
        for ip_address, data in json_resp.items():
            if isinstance(data, dict) and not data.get("bogon"):
                self._format_plus_details(data)
            self.cache[cache_key(ip_address)] = data
            result[ip_address] = Details(data)

    def _ensure_aiohttp_ready(self):
        """Ensures aiohttp internal state is initialized."""
        if self.httpsess:
            return

        timeout = aiohttp.ClientTimeout(total=self.request_options["timeout"])
        self.httpsess = aiohttp.ClientSession(timeout=timeout)
