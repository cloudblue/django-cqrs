#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

from importlib import import_module

import pytest
from six.moves import reload_module

from dj_cqrs.transport.base import BaseTransport


def test_no_transport_setting(settings):
    settings.CQRS = {}

    with pytest.raises(AttributeError) as e:
        reload_module(import_module('dj_cqrs.transport'))

    assert str(e.value) == 'CQRS transport is not set.'


def test_bad_transport_setting(settings):
    settings.CQRS = {'transport': '1221'}

    with pytest.raises(ImportError) as e:
        reload_module(import_module('dj_cqrs.transport'))

    assert str(e.value) == 'Bad CQRS transport class.'


class NoneBaseTransportCls(object):
    pass


def test_not_inherited_from_base_transport(settings):
    settings.CQRS = {'transport': 'tests.test_transport.test_base.NoneBaseTransportCls'}

    with pytest.raises(ImportError) as e:
        reload_module(import_module('dj_cqrs.transport'))

    assert str(e.value) == 'Bad CQRS transport class.'


def test_base_transport_consume():
    with pytest.raises(NotImplementedError):
        BaseTransport.consume(None)


def test_base_transport_produce():
    with pytest.raises(NotImplementedError):
        BaseTransport.produce(None)
