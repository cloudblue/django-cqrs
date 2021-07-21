#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import logging

from dj_cqrs.constants import DEFAULT_MASTER_AUTO_UPDATE_FIELDS, DEFAULT_MASTER_MESSAGE_TTL
from dj_cqrs.registries import MasterRegistry, ReplicaRegistry
from dj_cqrs.transport import BaseTransport

from django.utils.module_loading import import_string


logger = logging.getLogger('django-cqrs')


def validate_settings(settings):
    is_master = bool(MasterRegistry.models)
    is_replica = bool(ReplicaRegistry.models)
    if (not is_master) and (not is_replica):  # pragma: no cover
        return

    assert hasattr(settings, 'CQRS'), 'CQRS configuration must be set in Django project settings.'

    cqrs_settings = settings.CQRS
    assert isinstance(cqrs_settings, dict), 'CQRS configuration must be dict.'

    _validate_transport(cqrs_settings)

    if is_master:
        _validate_master(cqrs_settings)


def _validate_transport(cqrs_settings):
    transport_cls_location = cqrs_settings.get('transport')
    if not transport_cls_location:
        raise AssertionError('CQRS transport is not set.')

    transport = import_string(transport_cls_location)
    if not issubclass(transport, BaseTransport):
        raise AssertionError(
            'CQRS transport must be inherited from `dj_cqrs.transport.BaseTransport`.',
        )


def _validate_master(cqrs_settings):
    default_master_settings = {
        'master': {
            'CQRS_AUTO_UPDATE_FIELDS': DEFAULT_MASTER_AUTO_UPDATE_FIELDS,
            'CQRS_MESSAGE_TTL': DEFAULT_MASTER_MESSAGE_TTL,
            'correlation_function': None,
        },
    }

    if 'master' not in cqrs_settings:
        cqrs_settings.update(default_master_settings)
        return

    master_settings = cqrs_settings['master']
    assert isinstance(master_settings, dict), 'CQRS master configuration must be dict.'

    if 'CQRS_AUTO_UPDATE_FIELDS' in master_settings:
        assert isinstance(master_settings['CQRS_AUTO_UPDATE_FIELDS'], bool), (
            'CQRS master CQRS_AUTO_UPDATE_FIELDS must be bool.'
        )
    else:
        master_settings['CQRS_AUTO_UPDATE_FIELDS'] = DEFAULT_MASTER_AUTO_UPDATE_FIELDS

    if 'CQRS_MESSAGE_TTL' in master_settings:
        min_message_ttl = 1
        message_ttl = master_settings['CQRS_MESSAGE_TTL']
        if (message_ttl is not None) and (
            not isinstance(message_ttl, int) or message_ttl < min_message_ttl,
        ):
            # No error is raised for backward compatibility
            # TODO: raise error in 2.0.0
            logger.warning(
                'Settings CQRS_MESSAGE_TTL=%s is invalid, using default %s.',
                message_ttl, DEFAULT_MASTER_MESSAGE_TTL,
            )
            master_settings['CQRS_MESSAGE_TTL'] = DEFAULT_MASTER_MESSAGE_TTL
    else:
        master_settings['CQRS_MESSAGE_TTL'] = DEFAULT_MASTER_MESSAGE_TTL

    correlation_func = master_settings.get('correlation_function')
    if not correlation_func:
        master_settings['correlation_function'] = None
    elif not callable(correlation_func):
        raise AssertionError('CQRS master correlation_function must be callable.')
