# [<img src="https://ipinfo.io/static/ipinfo-small.svg" alt="IPinfo" width="24"/>](https://ipinfo.io/) IPinfo Python Client Library

This is the official Python client library for the IPinfo.io IP address API, allowing you to look up your own IP address, or get any of the following details for an IP:

 - [IP geolocation](https://ipinfo.io/ip-geolocation-api) (city, region, country, postal code, latitude, and longitude)
 - [ASN details](https://ipinfo.io/asn-api) (ISP or network operator, associated domain name, and type, such as business, hosting, or company)
 - [Firmographics data](https://ipinfo.io/ip-company-api) (the name and domain of the business that uses the IP address)
 - [Carrier information](https://ipinfo.io/ip-carrier-api) (the name of the mobile carrier and MNC and MCC for that carrier if the IP is used exclusively for mobile traffic)

## Getting Started

You'll need an IPinfo API access token, which you can get by signing up for a free account at [https://ipinfo.io/signup](https://ipinfo.io/signup).

The free plan is limited to 50,000 requests per month, and doesn't include some of the data fields such as IP type and company data. To enable all the data fields and additional request volumes see [https://ipinfo.io/pricing](https://ipinfo.io/pricing)

⚠️ Note: This library does not currently support our newest free API https://ipinfo.io/lite. If you’d like to use IPinfo Lite, you can call the [endpoint directly](https://ipinfo.io/developers/lite-api) using your preferred HTTP client. Developers are also welcome to contribute support for Lite by submitting a pull request.

### Installation

This package works with Python 3.5 or greater. However, we only officially
support non-EOL Python versions.

```bash
pip install ipinfo
```

### Quick Start

```python
>>> import ipinfo
>>> access_token = '123456789abc'
>>> handler = ipinfo.getHandler(access_token)
>>> ip_address = '216.239.36.21'
>>> details = handler.getDetails(ip_address)
>>> details.city
'Mountain View'
>>> details.loc
'37.3861,-122.0840'
```

#### Async/Await

An asynchronous handler is available as well, and can be accessed and used in
almost the same exact way as the synchronous handler:

```python
>>> import ipinfo
>>> access_token = '123456789abc'
>>> handler = ipinfo.getHandlerAsync(access_token)
>>> ip_address = '216.239.36.21'
>>> async def do_req():
...     details = await handler.getDetails(ip_address)
...     print(details.city)
...     print(details.loc)
...
>>>
>>> import asyncio
>>> loop = asyncio.get_event_loop()
>>> loop.run_until_complete(do_req())
Mountain View
37.4056,-122.0775
>>>
>>> ip_address = '1.1.1.1'
>>> loop.run_until_complete(do_req())
New York City
40.7143,-74.0060
```

Internally the library uses `aiohttp`, but as long as you provide an event
loop (as in this example via `asyncio`), it shouldn't matter.

### Usage

The `Handler.getDetails()` method accepts an IP address as an optional, positional argument. If no IP address is specified, the API will return data for the IP address from which it receives the request.

```python
>>> import ipinfo
>>> access_token = '123456789abc'
>>> handler = ipinfo.getHandler(access_token)
>>> details = handler.getDetails()
>>> details.city
'Mountain View'
>>> details.loc
'37.3861,-122.0840'
```

### Authentication

The IPinfo library can be authenticated with your IPinfo API token, which is passed in as a positional argument. It also works without an authentication token, but in a more limited capacity.

```python
>>> import ipinfo
>>> handler = ipinfo.getHandler(access_token='123456789abc')
```

### Details Data

`handler.getDetails()` will return a `Details` object that contains all fields listed in the [IPinfo developer docs](https://ipinfo.io/developers/responses#full-response) with a few minor additions. Properties can be accessed directly.

```python
>>> details.hostname
'any-in-2415.1e100.net'
```

#### Country Name

`details.country_name` will return the country name, as supplied by the `countries.json` file. See below for instructions on changing that file for use with non-English languages. `details.country` will still return a country code.

```python
>>> details.country
'US'
>>> details.country_name
'United States'
```

#### Longitude and Latitude

`details.latitude` and `details.longitude` will return latitude and longitude, respectively, as strings. `details.loc` will still return a composite string of both values.

```python
>>> details.loc
'37.3861,-122.0840'
>>> details.latitude
'37.3861'
>>> details.longitude
'-122.0840'
```

#### Accessing all properties

`details.all` will return all details data as a dictionary.

```python
>>> import pprint
>>> pprint.pprint(details.all)
{'abuse': {'address': 'US, CA, Mountain View, 1600 Amphitheatre Parkway, 94043',
           'country': 'US',
           'email': 'network-abuse@google.com',
           'name': 'Abuse',
           'network': '216.239.32.0/19',
           'phone': '+1-650-253-0000'},
 'asn': {'asn': 'AS15169',
         'domain': 'google.com',
         'name': 'Google LLC',
         'route': '216.239.36.0/24',
         'type': 'business'},
 'city': 'Mountain View',
 'company': {'domain': 'google.com', 'name': 'Google LLC', 'type': 'business'},
 'country': 'US',
 'country_name': 'United States',
 'hosting': {'host': 'google',
             'id': 'GOOGLE',
             'name': 'Google LLC',
             'network': '216.239.32.0/19'},
 'hostname': 'any-in-2415.1e100.net',
 'ip': '216.239.36.21',
 'latitude': '37.3861',
 'loc': '37.3861,-122.0840',
 'longitude': '-122.0840',
 'postal': '94035',
 'region': 'California',
 'timezone': 'America/Los_Angeles'}
```

### Caching

In-memory caching of `details` data is provided by default via the [cachetools](https://cachetools.readthedocs.io/en/latest/) library. This uses an LRU (least recently used) cache with a TTL (time to live) by default. This means that values will be cached for the specified duration; if the cache's max size is reached, cache values will be invalidated as necessary, starting with the oldest cached value.

#### Modifying cache options

Cache behavior can be modified by setting the `cache_options` keyword argument. `cache_options` is a dictionary in which the keys are keyword arguments specified in the `cachetools` library. The nesting of keyword arguments is to prevent name collisions between this library and its dependencies.

- Default maximum cache size: 4096 (multiples of 2 are recommended to increase efficiency)
- Default TTL: 24 hours (in seconds)

```python
>>> import ipinfo
>>> handler = ipinfo.getHandler(cache_options={'ttl':30, 'maxsize': 128})
```

#### Using a different cache

It's possible to use a custom cache by creating a child class of the [CacheInterface](https://github.com/ipinfo/python/blob/master/ipinfo/cache/interface.py) class and passing this into the handler object with the `cache` keyword argument. FYI this is known as [the Strategy Pattern](https://sourcemaking.com/design_patterns/strategy).

```python
import ipinfo
from ipinfo.cache.interface import CacheInterface

class MyCustomCache(CacheInterface):
    ...

handler = ipinfo.getHandler(cache=MyCustomCache())
```

#### Accessing the cache directly

You can access/update the cache directly via dictionary-like notation.

```python
>>> import ipinfo
>>> from ipinfo.handler_utils import cache_key
>>>
>>> access_token = '123456789abc'
>>> handler = ipinfo.getHandler(access_token)
>>> ip_cache_key = cache_key('1.1.1.1')

# Check if IP is in the cache.
>>> ip_cache_key in handler.cache
True

# Get the IP's details from cache.
>>> handler.cache[ip_cache_key]
{'ip': '1.1.1.1', 'hostname': 'one.one.one.one', 'anycast': True, 'city': 'Miami', 'region': 'Florida', 'country': 'US', 'loc': '25.7867,-80.1800', 'org': 'AS13335 Cloudflare, Inc.', 'postal': '33132', 'timezone': 'America/New_York', 'country_name': 'United States', 'latitude': '25.7867', 'longitude': '-80.1800'}

# Set the IP's details to something else in the cache.
>>> handler.cache[ip_cache_key] = None

# Delete the IP from the cache.
>>> del handler.cache[ip_cache_key]
```

### Modifying request options

**Note**: the asynchronous handler currently only accepts the `timeout` option,
input the same way as shown below.

Request behavior can be modified by setting the `request_options` keyword argument. `request_options` is a dictionary in which the keys are keyword arguments specified in the `requests` library. The nesting of keyword arguments is to prevent name collisions between this library and its dependencies.

- Default request timeout: 2 seconds

```python
>>> handler = ipinfo.getHandler(request_options={'timeout': 4})
```

### Custom Headers

You can add custom headers or modify default headers by setting the `headers` keyword argument when initializing the handler. `headers` is a dictionary of `{'header': 'value'}` format.

```python
>>> handler = ipinfo.getHandler(headers={'user-agent': 'My Custom User-agent', 'custom_header': 'yes'})
```

### Internationalization

When looking up an IP address, the response object includes `details.country_name`, `details.isEU`, `details.country_flag`, `details.country_flag_url` and `details.country_currency` attributes which includes the country based on American English. It is possible to return the country name in other languages by setting the `countries`, remove or add EU countries by setting the keyword argument `eu_countries`, change the country flag emoji or unicode by setting the keyword argument `countries_flags` or change country's currency code or currency symbol by setting the `countries_currencies` when creating the `IPinfo` object. Moreover, the response object includes a `details.continent` which includes continent code and name of IP. The default file can be changed by setting the `continent` while creating the `IPinfo` object.

```python
>>> import ipinfo
# Country Names: In-memory map
>>> countries = {
    "BD": "Bangladesh",
    "BE": "Belgium",
    "BF": "Burkina Faso",
    ...
}

# EU Countries: In-memory list
>>> eu_countries = [
    "IE",
    "AT",
    "LT",
    ...
]

# Country Flags: In-memory map
>>> countries_flags = {
    "AD": {"emoji": "🇦🇩", "unicode": "U+1F1E6 U+1F1E9"},
    "AE": {"emoji": "🇦🇪", "unicode": "U+1F1E6 U+1F1EA"},
    "AF": {"emoji": "🇦🇫", "unicode": "U+1F1E6 U+1F1EB"},
    ...
}

# Country Currencies: In-memory map
>>> countries_currencies = {
    "AD": {"code": "EUR", "symbol": "€"},
    "AE": {"code": "AED", "symbol": "د.إ"},
    "AF": {"code": "AFN", "symbol": "؋"},
    ...
}

# Continents: In-memory map
>>> continents = {
    "BD": {"code": "AS", "name": "Asia"},
    "BE": {"code": "EU", "name": "Europe"},
    "BF": {"code": "AF", "name": "Africa"},
    ...
}

# create handler
>>> access_token = '123456789abc'
>>> handler = ipinfo.getHandler(
    access_token,
    countries=countries,
    eu_countries=eu_countries,
    countries_flags=countries_flags,
    countries_currencies=countries_currencies,
    continents=continents
)
```
### Batch Operations

Looking up a single IP at a time can be slow. It could be done concurrently
from the client side, but IPinfo supports a batch endpoint to allow you to
group together IPs and let us handle retrieving details for them in bulk for
you.

```python
>>> import ipinfo, pprint
>>> access_token = '123456789abc'
>>> handler = ipinfo.getHandler(access_token)
>>> pprint.pprint(handler.getBatchDetails([
...   '1.1.1.1',
...   '8.8.8.8',
...   '1.2.3.4/country',
... ]))
{'1.1.1.1': {'city': '',
             'country': 'AU',
             'country_name': 'Australia',
             'hostname': 'one.one.one.one',
             'ip': '1.1.1.1',
             'latitude': '-33.4940',
             'loc': '-33.4940,143.2100',
             'longitude': '143.2100',
             'org': 'AS13335 Cloudflare, Inc.',
             'region': ''},
 '1.2.3.4/country': 'US',
 '8.8.8.8': {'city': 'Mountain View',
             'country': 'US',
             'country_name': 'United States',
             'hostname': 'dns.google',
             'ip': '8.8.8.8',
             'latitude': '37.3860',
             'loc': '37.3860,-122.0838',
             'longitude': '-122.0838',
             'org': 'AS15169 Google LLC',
             'postal': '94035',
             'region': 'California',
             'timezone': 'America/Los_Angeles'}}
```

The input size is not limited, as the interface will chunk operations for you
behind the scenes.

Please see [the official documentation](https://ipinfo.io/developers/batch) for
more information and limitations.

## Other Libraries

There are official [IPinfo client libraries](https://ipinfo.io/developers/libraries) available for many languages including PHP, Go, Java, Ruby, and many popular frameworks such as Django, Rails, and Laravel. There are also many third-party libraries and integrations available for our API.

## About IPinfo

Founded in 2013, IPinfo prides itself on being the most reliable, accurate, and in-depth source of IP address data available anywhere. We process terabytes of data to produce our custom IP geolocation, company, carrier, VPN detection, hosted domains, and IP type data sets. Our API handles over 40 billion requests a month for 100,000 businesses and developers.

[![image](https://avatars3.githubusercontent.com/u/15721521?s=128&u=7bb7dde5c4991335fb234e68a30971944abc6bf3&v=4)](https://ipinfo.io/)
