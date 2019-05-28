from __future__ import unicode_literals

from importlib import import_module

import pytest
from six.moves import reload_module


def test_no_transport_setting(settings):
    settings.CQRS = {}
    with pytest.raises(AttributeError) as e:
        reload_module(import_module('dj_cqrs.transport'))
    assert str(e.value) == 'CQRS transport is not setup.'


def test_bad_transport_setting(settings):
    settings.CQRS = {'transport': {'class': '1221'}}
    with pytest.raises(ImportError) as e:
        reload_module(import_module('dj_cqrs.transport'))
    assert str(e.value) == 'Bad CQRS transport class.'
