"""
Main API client asynchronous handler for fetching data from the IPinfo service.
"""

from ipaddress import IPv4Address, IPv6Address

import aiohttp

from .error import APIError
from .cache.default import DefaultCache
from .details import Details
from .exceptions import RequestQuotaExceededError
from .handler_utils import (
    CACHE_MAXSIZE,
    CACHE_TTL,
    LITE_API_URL,
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


class AsyncHandlerLite:
    """
    Allows client to request data for specified IP address asynchronously using the Lite API.
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
        if isinstance(ip_address, IPv4Address) or isinstance(ip_address, IPv6Address):
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
        url = f"{LITE_API_URL}/{ip_address}" if ip_address else f"{LITE_API_URL}/me"
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

    def _ensure_aiohttp_ready(self):
        """Ensures aiohttp internal state is initialized."""
        if self.httpsess:
            return

        timeout = aiohttp.ClientTimeout(total=self.request_options["timeout"])
        self.httpsess = aiohttp.ClientSession(timeout=timeout)
