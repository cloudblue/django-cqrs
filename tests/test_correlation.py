#  Copyright © 2023 Ingram Micro Inc. All rights reserved.

from importlib import import_module, reload

from dj_cqrs.correlation import get_correlation_id


def test_default_correlation():
    assert get_correlation_id(None, None, None, None) is None


def test_custom_correlation(settings):
    previous_cqrs_settings = settings.CQRS
    settings.CQRS = {'master': {'correlation_function': lambda *args: '1q2w3e'}}

    reload(import_module('dj_cqrs.correlation'))
    assert get_correlation_id(None, None, None, None) == '1q2w3e'

    settings.CQRS = previous_cqrs_settings
    reload(import_module('dj_cqrs.correlation'))
