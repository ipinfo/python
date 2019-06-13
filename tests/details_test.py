import pytest

from ipinfo.details import Details


def test_init():
    data = {"foo": "bar"}
    details = Details(data)
    assert details.details == data


def test_getattr_success():
    data = {"foo": "bar"}
    details = Details(data)
    assert details.foo == data["foo"]


def test_getattr_fail():
    data = {"foo": "bar"}
    details = Details(data)
    with pytest.raises(Exception):
        details.blah


def test_all():
    data = {"foo": "bar", "ham": "eggs"}
    details = Details(data)
    assert details.all == data
