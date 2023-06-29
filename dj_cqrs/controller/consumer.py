#  Copyright © 2023 Ingram Micro Inc. All rights reserved.

import copy
import logging
from contextlib import ExitStack

from django.conf import settings
from django.db import Error, close_old_connections, transaction

from dj_cqrs.constants import SignalType
from dj_cqrs.logger import log_timed_out_queries
from dj_cqrs.registries import ReplicaRegistry
from dj_cqrs.utils import apply_query_timeouts


logger = logging.getLogger('django-cqrs')


def consume(payload):
    """Consumer controller.

    :param dj_cqrs.dataclasses.TransportPayload payload: Consumed payload from master service.
    """
    payload = copy.deepcopy(payload)
    return route_signal_to_replica_model(
        payload.signal_type,
        payload.cqrs_id,
        payload.instance_data,
        previous_data=payload.previous_data,
        meta=payload.meta,
        queue=payload.queue,
    )


def route_signal_to_replica_model(
    signal_type,
    cqrs_id,
    instance_data,
    previous_data=None,
    meta=None,
    queue=None,
):
    """Routes signal to model method to create/update/delete replica instance.

    :param dj_cqrs.constants.SignalType signal_type: Consumed signal type.
    :param str cqrs_id: Replica model CQRS unique identifier.
    :param dict instance_data: Master model data.
    :param dict or None previous_data: Previous model data for changed tracked fields, if exists.
    :param dict or None meta: Payload metadata, if exists.
    :param str or None queue: Synced queue.
    """
    if signal_type not in (SignalType.DELETE, SignalType.SAVE, SignalType.SYNC):
        logger.error('Bad signal type "{0}" for CQRS_ID "{1}".'.format(signal_type, cqrs_id))
        return

    model_cls = ReplicaRegistry.get_model_by_cqrs_id(cqrs_id)
    if not model_cls:
        return

    this_queue = settings.CQRS['queue']
    if signal_type == SignalType.SYNC and model_cls.CQRS_ONLY_DIRECT_SYNCS and queue != this_queue:
        return True

    db_is_needed = not model_cls.CQRS_NO_DB_OPERATIONS
    if db_is_needed:
        close_old_connections()

    is_meta_supported = model_cls.CQRS_META
    try:
        if db_is_needed:
            apply_query_timeouts(model_cls)

        with transaction.atomic(savepoint=False) if db_is_needed else ExitStack():
            if signal_type == SignalType.DELETE:
                if is_meta_supported:
                    return model_cls.cqrs_delete(instance_data, meta=meta)

                return model_cls.cqrs_delete(instance_data)

            f_kw = {'previous_data': previous_data}
            if is_meta_supported:
                f_kw['meta'] = meta

            if signal_type == SignalType.SAVE:
                return model_cls.cqrs_save(instance_data, **f_kw)

            if signal_type == SignalType.SYNC:
                f_kw['sync'] = True
                return model_cls.cqrs_save(instance_data, **f_kw)

    except Error as e:
        pk_name = getattr(model_cls._meta.pk, 'name', 'id')
        pk_value = instance_data.get(pk_name)
        cqrs_revision = instance_data.get('cqrs_revision')

        logger.error(
            '{0}\nCQRS {1} error: pk = {2}, cqrs_revision = {3} ({4}).'.format(
                str(e),
                signal_type,
                pk_value,
                cqrs_revision,
                model_cls.CQRS_ID,
            ),
        )

        log_timed_out_queries(e, model_cls)
