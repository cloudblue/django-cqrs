#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import copy
import logging
from contextlib import ExitStack

from dj_cqrs.constants import SignalType
from dj_cqrs.registries import ReplicaRegistry

from django.db import Error, close_old_connections, transaction


logger = logging.getLogger('django-cqrs')


def consume(payload):
    """ Consumer controller.

    :param dj_cqrs.dataclasses.TransportPayload payload: Consumed payload from master service.
    """
    payload = copy.deepcopy(payload)
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
        logger.error('Bad signal type "{0}" for CQRS_ID "{1}".'.format(signal_type, cqrs_id))
        return

    model_cls = ReplicaRegistry.get_model_by_cqrs_id(cqrs_id)
    if model_cls:
        db_is_needed = not model_cls.CQRS_NO_DB_OPERATIONS
        if db_is_needed:
            close_old_connections()

        try:
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
        except Error as e:
            pk_value = instance_data.get(model_cls._meta.pk.name)
            cqrs_revision = instance_data.get('cqrs_revision')

            logger.error(
                '{0}\nCQRS {1} error: pk = {2}, cqrs_revision = {3} ({4}).'.format(
                    str(e), signal_type, pk_value, cqrs_revision, model_cls.CQRS_ID,
                ),
            )
