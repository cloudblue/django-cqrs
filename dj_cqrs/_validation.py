#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import logging

from dj_cqrs.constants import (
    DEFAULT_MASTER_AUTO_UPDATE_FIELDS,
    DEFAULT_MASTER_MESSAGE_TTL,
    DEFAULT_REPLICA_DELAY_QUEUE_MAX_SIZE,
    DEFAULT_REPLICA_MAX_RETRIES,
    DEFAULT_REPLICA_RETRY_DELAY,
)
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

    if is_replica:
        _validate_replica(cqrs_settings)


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
            not isinstance(message_ttl, int) or message_ttl < min_message_ttl
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


def _validate_replica(cqrs_settings):
    queue = cqrs_settings.get('queue')
    assert queue, 'CQRS queue is not set.'
    assert isinstance(queue, str), 'CQRS queue must be string.'

    default_replica_settings = {
        'replica': {
            'CQRS_MAX_RETRIES': DEFAULT_REPLICA_MAX_RETRIES,
            'CQRS_RETRY_DELAY': DEFAULT_REPLICA_RETRY_DELAY,
            'CQRS_DELAY_QUEUE_MAX_SIZE': DEFAULT_REPLICA_DELAY_QUEUE_MAX_SIZE,
        },
    }

    if 'replica' not in cqrs_settings:
        cqrs_settings.update(default_replica_settings)
        return

    replica_settings = cqrs_settings['replica']
    assert isinstance(replica_settings, dict), 'CQRS replica configuration must be dict.'

    if 'CQRS_MAX_RETRIES' in replica_settings:
        min_retries = 0
        max_retries = replica_settings['CQRS_MAX_RETRIES']
        if (max_retries is not None) and (
            not isinstance(max_retries, int) or max_retries < min_retries
        ):
            # No error is raised for backward compatibility
            # TODO: raise error in 2.0.0
            logger.warning(
                'Replica setting CQRS_MAX_RETRIES=%s is invalid, using default %s.',
                max_retries, DEFAULT_REPLICA_MAX_RETRIES,
            )
            replica_settings['CQRS_MAX_RETRIES'] = DEFAULT_REPLICA_MAX_RETRIES
    else:
        replica_settings['CQRS_MAX_RETRIES'] = DEFAULT_REPLICA_MAX_RETRIES

    min_retry_delay = 0
    retry_delay = replica_settings.get('CQRS_RETRY_DELAY')
    if 'CQRS_RETRY_DELAY' not in replica_settings:
        replica_settings['CQRS_RETRY_DELAY'] = DEFAULT_REPLICA_RETRY_DELAY
    elif not isinstance(retry_delay, int) or retry_delay < min_retry_delay:
        # No error is raised for backward compatibility
        # TODO: raise error in 2.0.0
        logger.warning(
            'Replica setting CQRS_RETRY_DELAY=%s is invalid, using default %s.',
            retry_delay, DEFAULT_REPLICA_RETRY_DELAY,
        )
        replica_settings['CQRS_RETRY_DELAY'] = DEFAULT_REPLICA_RETRY_DELAY

    # delay_queue_max_size - is the wrong name for CQRS_DELAY_QUEUE_MAX_SIZE,
    #  which is supported for backward compatibility
    # TODO: drop `delay_queue_max_size` in 2.0.0
    min_delay_size = 0
    delay_size = replica_settings.get(
        'CQRS_DELAY_QUEUE_MAX_SIZE', replica_settings.get('delay_queue_max_size'),
    )
    if delay_size is None:
        set_delay_size = DEFAULT_REPLICA_DELAY_QUEUE_MAX_SIZE
    elif not isinstance(delay_size, int) or delay_size <= min_delay_size:
        logger.warning(
            'Settings delay_queue_max_size=%s is invalid, using default %s.',
            delay_size, DEFAULT_REPLICA_DELAY_QUEUE_MAX_SIZE,
        )
        set_delay_size = DEFAULT_REPLICA_DELAY_QUEUE_MAX_SIZE
    else:
        set_delay_size = delay_size
    replica_settings['CQRS_DELAY_QUEUE_MAX_SIZE'] = set_delay_size
