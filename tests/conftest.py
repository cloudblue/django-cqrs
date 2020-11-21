from copy import deepcopy

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
