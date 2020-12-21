# IPInfo Changelog

## 4.1.0

- Most private functions on all handlers (i.e. those that start with `_`) are
  now moved to `ipinfo.handler_utils`.
- All constants that existed on handlers (i.e. `REQUEST_TIMEOUT_DEFAULT`) are
  now moved to `ipinfo.handler_utils`.
- Both the sync and async handlers have the following improvements:
    - `timeout` can be specified as a keyword-arg to getDetails to optionally
      override the client-level timeout.
    - getBatchDetails now has no limit to the size of the `ip_addresses` input
      list. It will chunk the list internally and make requests against the
      batch endpoint in a way that doesn't exceed the API's own limits.
    - getBatchDetails now accepts the new options `batch_size`,
      `timeout_per_batch`, `timeout_total` and `raise_on_fail`. Please see the
      documentation for details on what each of these do.

## 4.0.0

#### Breaking Changes

- [PR #32](https://github.com/ipinfo/python/pull/32)
  All EOL Python versions are no longer supported; currently, Python 3.6 or
  greater is now **required**.
  An asynchronous handler is available from `getHandlerAsync` which returns an
  `AsyncHandler` which uses **aiohttp**.

## 3.0.0

#### Breaking Changes

- [PR #19](https://github.com/ipinfo/python/pull/19)
  DefaultCache requires keyword arguments now instead of positional arguments,
  in particular `maxsize` and `ttl`.

#### Bug Fix

- [PR #19](https://github.com/ipinfo/python/pull/19)
  [Issue #18](https://github.com/ipinfo/python/issues/18)
  An issue with the handler not being created if you provide your own custom
  `maxsize`/`ttl` values has been fixed.

## 2.1.0

#### General

- Released a batch ops function on the handler called `getBatchDetails` which
  accepts a list of IP addresses (or an IP address plus a path to more specific
  details, e.g. `8.8.8.8/country`). See documentation on batch operations in the
  README for more details.

## 2.0.0

#### Breaking Changes

- Fix [Issue #8](https://github.com/ipinfo/python/issues/8).
  Deleted the `ip_address` key in the details object which was of type [`IPv4Address`](https://docs.python.org/3/library/ipaddress.html).

  This allows serializing the details object (into JSON or something else) without errors by default.

  Users who expected that object type can simply pull the `ip` key instead and turn it into an [`IPv4Address`](https://docs.python.org/3/library/ipaddress.html)
  object on their own.
