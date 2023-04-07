#  Copyright © 2023 Ingram Micro Inc. All rights reserved.

from copy import deepcopy

import django
import pytest


@pytest.fixture(autouse=True)
def restore_cqrs_settings(settings):
    """Adhoc solution for restoring CQRS settings after each test

    Pytest-Django don't track settings change for mutable objects (settings.CQRS['queue'] = ...).
    Fixture triggers SettingsWrapper to register change before test run and restore it after.
    """
    if hasattr(settings, 'CQRS'):
        settings.CQRS = deepcopy(settings.CQRS)

    yield


@pytest.fixture()
def django_v_trans_q_count_sup():
    return 2 if django.get_version() >= '4.2' else 0
