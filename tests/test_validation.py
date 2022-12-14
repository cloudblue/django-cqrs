#  Copyright © 2022 Ingram Micro Inc. All rights reserved.

from unittest.mock import MagicMock

import pytest

from dj_cqrs._validation import validate_settings


def test_full_configuration():
    def f(*a, **kw):
        pass

    settings = MagicMock(CQRS={
        'queue': 'start',

        'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
        'host': 'host',
        'port': 1234,
        'user': 'user',
        'password': 'pswd',

        'master': {
            'CQRS_AUTO_UPDATE_FIELDS': True,
            'CQRS_MESSAGE_TTL': 10,
            'correlation_function': f,
            'meta_function': f,
        },

        'replica': {
            'CQRS_MAX_RETRIES': 5,
            'CQRS_RETRY_DELAY': 4,
            'delay_queue_max_size': 2,
        },
    })

    validate_settings(settings)


def test_configuration_does_not_exist():
    with pytest.raises(AssertionError) as e:
        validate_settings({})

    assert str(e.value) == 'CQRS configuration must be set in Django project settings.'


@pytest.mark.parametrize('value', ([], 'settings'))
def test_configuration_has_wrong_type(value):
    with pytest.raises(AssertionError) as e:
        validate_settings(MagicMock(CQRS=value))

    assert str(e.value) == 'CQRS configuration must be dict.'


def test_transport_is_not_set():
    with pytest.raises(AssertionError) as e:
        validate_settings(MagicMock(CQRS={}))

    assert str(e.value) == 'CQRS transport is not set.'


def test_transport_is_not_importable():
    with pytest.raises(ImportError):
        validate_settings(MagicMock(CQRS={'transport': 'abc'}))


def test_transport_has_wrong_inheritance():
    with pytest.raises(AssertionError) as e:
        validate_settings(MagicMock(CQRS={'transport': 'dj_cqrs.dataclasses.TransportPayload'}))

    assert str(e.value) == (
        'CQRS transport must be inherited from `dj_cqrs.transport.BaseTransport`.'
    )


@pytest.fixture
def cqrs_settings():
    return MagicMock(CQRS={
        'transport': 'dj_cqrs.transport.mock.TransportMock',
        'queue': 'replica',
    })


def test_master_configuration_not_set(cqrs_settings):
    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['master'] == {
        'CQRS_AUTO_UPDATE_FIELDS': False,
        'CQRS_MESSAGE_TTL': 86400,
        'correlation_function': None,
        'meta_function': None,
    }


@pytest.mark.parametrize('value', ([], 'settings', None))
def test_master_configuration_has_wrong_type(cqrs_settings, value):
    cqrs_settings.CQRS['master'] = value

    with pytest.raises(AssertionError) as e:
        validate_settings(cqrs_settings)

    assert str(e.value) == 'CQRS master configuration must be dict.'


def test_master_configuration_is_empty(cqrs_settings):
    cqrs_settings.CQRS['master'] = {}

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['master'] == {
        'CQRS_AUTO_UPDATE_FIELDS': False,
        'CQRS_MESSAGE_TTL': 86400,
        'correlation_function': None,
        'meta_function': None,
    }


@pytest.mark.parametrize('value', (None, 'true', 1))
def test_master_auto_update_fields_has_wrong_type(cqrs_settings, value):
    cqrs_settings.CQRS['master'] = {'CQRS_AUTO_UPDATE_FIELDS': value}

    with pytest.raises(AssertionError) as e:
        validate_settings(cqrs_settings)

    assert str(e.value) == 'CQRS master CQRS_AUTO_UPDATE_FIELDS must be bool.'


def test_master_message_ttl_is_none(cqrs_settings):
    cqrs_settings.CQRS['master'] = {
        'CQRS_AUTO_UPDATE_FIELDS': True,
        'CQRS_MESSAGE_TTL': None,
    }

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['master'] == {
        'CQRS_AUTO_UPDATE_FIELDS': True,
        'CQRS_MESSAGE_TTL': None,
        'correlation_function': None,
        'meta_function': None,
    }


@pytest.mark.parametrize('value', ({}, 1.23, -2, 0))
def test_master_message_ttl_has_wrong_type_or_invalid_value(value, cqrs_settings, caplog):
    cqrs_settings.CQRS['master'] = {'CQRS_MESSAGE_TTL': value}

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['master'] == {
        'CQRS_AUTO_UPDATE_FIELDS': False,
        'CQRS_MESSAGE_TTL': 86400,
        'correlation_function': None,
        'meta_function': None,
    }
    assert caplog.record_tuples


def test_master_correlation_func_is_not_callable(cqrs_settings):
    cqrs_settings.CQRS['master'] = {'correlation_function': 'x'}

    with pytest.raises(AssertionError) as e:
        validate_settings(cqrs_settings)

    assert str(e.value) == 'CQRS master correlation_function must be callable.'


def test_master_correlation_func_is_callable(cqrs_settings):
    cqrs_settings.CQRS['master'] = {'correlation_function': lambda: 1}

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['master']['correlation_function']() == 1


def test_master_meta_func_is_func_from_string(cqrs_settings):
    cqrs_settings.CQRS['master'] = {'meta_function': 'tests.utils.db_error'}

    validate_settings(cqrs_settings)

    assert callable(cqrs_settings.CQRS['master']['meta_function'])


def test_master_meta_func_is_func(cqrs_settings):
    cqrs_settings.CQRS['master'] = {'meta_function': lambda **kw: 1}

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['master']['meta_function']() == 1


def test_master_meta_func_is_non_importable_from_string(cqrs_settings):
    cqrs_settings.CQRS['master'] = {'meta_function': 'random.stuff'}

    with pytest.raises(AssertionError) as e:
        validate_settings(cqrs_settings)

    assert str(e.value) == 'CQRS master meta_function import error.'


@pytest.mark.parametrize('f', ('dj_cqrs.dataclasses.TransportPayload', 5))
def test_master_meta_func_is_not_func(cqrs_settings, f):
    cqrs_settings.CQRS['master'] = {'meta_function': f}

    with pytest.raises(AssertionError) as e:
        validate_settings(cqrs_settings)

    assert str(e.value) == 'CQRS master meta_function must be function.'


@pytest.mark.parametrize('f', ('dj_cqrs.utils.get_message_expiration_dt', lambda: 1))
def test_master_meta_func_must_support_kwargs(cqrs_settings, f):
    cqrs_settings.CQRS['master'] = {'meta_function': f}

    with pytest.raises(AssertionError) as e:
        validate_settings(cqrs_settings)

    assert str(e.value) == 'CQRS master meta_function must support **kwargs.'


def test_replica_configuration_not_set(cqrs_settings):
    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['replica'] == {
        'CQRS_MAX_RETRIES': 30,
        'CQRS_RETRY_DELAY': 2,
        'delay_queue_max_size': 1000,
    }


@pytest.mark.parametrize('value', ([], 'settings', None))
def test_replica_configuration_has_wrong_type(cqrs_settings, value):
    cqrs_settings.CQRS['replica'] = value

    with pytest.raises(AssertionError) as e:
        validate_settings(cqrs_settings)

    assert str(e.value) == 'CQRS replica configuration must be dict.'


def test_replica_configuration_is_empty(cqrs_settings):
    cqrs_settings.CQRS['replica'] = {}

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['replica'] == {
        'CQRS_MAX_RETRIES': 30,
        'CQRS_RETRY_DELAY': 2,
        'delay_queue_max_size': 1000,
    }


def test_replica_max_retries_is_none(cqrs_settings):
    cqrs_settings.CQRS['replica'] = {'CQRS_MAX_RETRIES': None}

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['replica']['CQRS_MAX_RETRIES'] is None


@pytest.mark.parametrize('value', ({}, 1.23, -2))
def test_replica_max_retries_has_wrong_type_or_invalid_value(value, cqrs_settings, caplog):
    cqrs_settings.CQRS['replica'] = {
        'CQRS_MAX_RETRIES': value,
        'CQRS_RETRY_DELAY': 10,
        'delay_queue_max_size': value,
    }

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['replica'] == {
        'CQRS_MAX_RETRIES': 30,
        'CQRS_RETRY_DELAY': 10,
        'delay_queue_max_size': 1000,
    }
    assert caplog.record_tuples


def test_replica_retry_delay_is_none(cqrs_settings):
    cqrs_settings.CQRS['replica'] = {'CQRS_RETRY_DELAY': None}

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['replica']['CQRS_RETRY_DELAY'] == 2


@pytest.mark.parametrize('value', ({}, 1.23, -2))
def test_replica_retry_delay_has_wrong_type_or_invalid_value(value, cqrs_settings, caplog):
    cqrs_settings.CQRS['replica'] = {
        'CQRS_MAX_RETRIES': 0,
        'CQRS_RETRY_DELAY': value,
        'delay_queue_max_size': 1,
    }

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['replica'] == {
        'CQRS_MAX_RETRIES': 0,
        'CQRS_RETRY_DELAY': 2,
        'delay_queue_max_size': 1,
    }
    assert caplog.record_tuples


def test_replica_delay_queue_max_size_is_none(cqrs_settings):
    cqrs_settings.CQRS['replica'] = {'delay_queue_max_size': None}

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['replica']['delay_queue_max_size'] is None


@pytest.mark.parametrize('value', ({}, 1.23, -2))
def test_replica_delay_queue_max_size_has_wrong_type_or_invalid_value(value, cqrs_settings, caplog):
    cqrs_settings.CQRS['replica'] = {
        'CQRS_RETRY_DELAY': 0,
        'delay_queue_max_size': value,
    }

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['replica'] == {
        'CQRS_MAX_RETRIES': 30,
        'CQRS_RETRY_DELAY': 0,
        'delay_queue_max_size': 1000,
    }
    assert caplog.record_tuples


def test_replica_delay_queue_max_size_deprecated_parameter(cqrs_settings):
    cqrs_settings.CQRS['replica'] = {'delay_queue_max_size': 200}

    validate_settings(cqrs_settings)

    assert cqrs_settings.CQRS['replica']['delay_queue_max_size'] == 200
