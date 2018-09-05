The official Python library for the `IPinfo <https://ipinfo.io/>`_ API.
###########################################################################

`ipinfo_wrapper` is a lightweight wrapper for the IPinfo API, which provides up-to-date IP address data.

.. contents::

.. section-numbering::

Usage
=====

The `Handler.getDetails()` method accepts an IP address as an optional, positional argument. If no IP address is specified, the API will return data for the IP address from which it receives the request.

>>> import ipinfo_wrapper
>>> access_token = '123456789abc'
>>> handler = ipinfo_wrapper.getHandler(access_token)
>>> ip_address = '216.239.36.21'
>>> details = handler.getDetails(ip_address)
>>> details.city
Emeryville
>>> details.loc
37.8342,-122.2900

Authentication
==============
The IPinfo library can be authenticated with your IPinfo API token, which is passed in as a positional argument. It also works without an authentication token, but in a more limited capacity.

>>> access_token = '123456789abc'
>>> handler = ipinfo_wrapper.getHandler(access_token)


Details Data
=============
`handler.getDetails()` will return a `Details` object that contains all fields listed `IPinfo developer docs <https://ipinfo.io/developers/responses#full-response>`_ with a few minor additions. Properties can be accessed directly.

>>> details.hostname
cpe-104-175-221-247.socal.res.rr.com


Country Name
------------

`details.country_name` will return the country name, as supplied by the `countries.json` file. See below for instructions on changing that file for use with non-English languages. `details.country` will still return country code.

>>> details.country
US
>>> details.country_name
United States

IP Address
----------

`details.ip_address` will return the an `ipaddress` object from the `Python Standard Library <https://docs.python.org/3/library/ipaddress.html>`_. `details.ip` will still return a string.

>>> details.ip
104.175.221.247
>>> type(details.ip)
<class 'str'>
>>> details.ip_address
104.175.221.247
>>> type(details.ip_address)
<class 'ipaddress.IPv4Address'>

Longitude and Latitude
----------------------

`details.latitude` and `details.longitude` will return latitude and longitude, respectively, as strings. `details.loc` will still return a composite string of both values.

>>> details.loc
34.0293,-118.3570
>>> details.latitude
34.0293
>>> details.longitude
-118.3570

Accessing all properties
------------------------

`details.all` will return all details data as a dictionary.

>>> details.all
    {
    'asn': {  'asn': 'AS20001',
               'domain': 'twcable.com',
               'name': 'Time Warner Cable Internet LLC',
               'route': '104.172.0.0/14',
               'type': 'isp'},
    'city': 'Los Angeles',
    'company': {   'domain': 'twcable.com',
                   'name': 'Time Warner Cable Internet LLC',
                   'type': 'isp'},
    'country': 'US',
    'country_name': 'United States',
    'hostname': 'cpe-104-175-221-247.socal.res.rr.com',
    'ip': '104.175.221.247',
    'ip_address': IPv4Address('104.175.221.247'),
    'loc': '34.0293,-118.3570',
    'latitude': '34.0293',
    'longitude': '-118.3570',
    'phone': '323',
    'postal': '90016',
    'region': 'California'
    }

Caching
=======
In-memory caching of `details` data is provided by default via the `cachetools <https://cachetools.readthedocs.io/en/latest/>`_ library. This uses an LRU (least recently used) cache with a TTL (time to live) by default. This means that values will be cached for the specified duration; if the cache's max size is reached, cache values will be invalidated as necessary, starting with the oldest cached value.

Modifying cache options
-----------------------

Cache behavior can be modified by setting the `cache_options` keyword argument. `cache_options` is a dictionary in which the keys are keyword arguments specified in the `cachetools` library. The nesting of keyword arguments is to prevent name collisions between this library and its dependencies.

* Default maximum cache size: 4096 (multiples of 2 are recommended to increase efficiency)
* Default TTL: 24 hours (in seconds)

>>> handler = ipinfo_wrapper.getHandler(cache_options={'ttl':30, 'maxsize': 128})

Using a different cache
-----------------------

It's possible to use a custom cache by creating a child class of the `CacheInterface <https://github.com/jhtimmins/ipinfo-python/blob/master/cache/interface.py>`_ class and passing this into the handler object with the `cache` keyword argument. FYI this is known as `the Strategy Pattern <https://sourcemaking.com/design_patterns/strategy>`_.

>>> handler = ipinfo_wrapper.getHandler(cache=my_fancy_custom_class)


Internationalization
====================
When looking up an IP address, the response object includes a `details.country_name` attribute which includes the country name based on American English. It is possible to return the country name in other languages by setting the `countries_file` keyword argument when creating the `IPinfo` object.

The file must be a `.json` file with the following structure::

    {
     "BD": "Bangladesh",
     "BE": "Belgium",
     "BF": "Burkina Faso",
     "BG": "Bulgaria"
     ...
    }
