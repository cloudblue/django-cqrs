#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import logging
from contextlib import ExitStack

from django.db import close_old_connections, transaction

from dj_cqrs.constants import SignalType
from dj_cqrs.registries import ReplicaRegistry

logger = logging.getLogger('django-cqrs')


def consume(payload):
    """ Consumer controller.

    :param dj_cqrs.dataclasses.TransportPayload payload: Consumed payload from master service.
    """
    return route_signal_to_replica_model(
        payload.signal_type, payload.cqrs_id, payload.instance_data,
        previous_data=payload.previous_data,
    )


def route_signal_to_replica_model(signal_type, cqrs_id, instance_data, previous_data=None):
    """ Routes signal to model method to create/update/delete replica instance.

    :param dj_cqrs.constants.SignalType signal_type: Consumed signal type.
    :param str cqrs_id: Replica model CQRS unique identifier.
    :param dict instance_data: Master model data.
    """
    if signal_type not in (SignalType.DELETE, SignalType.SAVE, SignalType.SYNC):
        logger.error('Bad signal type "{}" for CQRS_ID "{}".'.format(signal_type, cqrs_id))
        return

    model_cls = ReplicaRegistry.get_model_by_cqrs_id(cqrs_id)
    if model_cls:
        db_is_needed = not model_cls.CQRS_NO_DB_OPERATIONS
        if db_is_needed:
            close_old_connections()

        with transaction.atomic(savepoint=False) if db_is_needed else ExitStack():
            if signal_type == SignalType.DELETE:
                return model_cls.cqrs_delete(instance_data)

            elif signal_type == SignalType.SAVE:
                return model_cls.cqrs_save(instance_data, previous_data=previous_data)

            elif signal_type == SignalType.SYNC:
                return model_cls.cqrs_save(
                    instance_data,
                    previous_data=previous_data,
                    sync=True,
                )
