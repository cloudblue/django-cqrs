from __future__ import unicode_literals

import logging

from dj_cqrs.constants import SignalType
from dj_cqrs.registries import ReplicaRegistry


logger = logging.getLogger()


def consume(payload):
    """ Consumer controller.

    :param dj_cqrs.dataclasses.TransportPayload payload: Consumed payload from master service.
    """
    route_signal_to_replica_model(payload.signal_type, payload.cqrs_id, payload.instance_data)


def route_signal_to_replica_model(signal_type, cqrs_id, instance_data):
    """ Routes signal to model method to create/update/delete replica instance.

    :param dj_cqrs.constants.SignalType signal_type: Consumed signal type.
    :param str cqrs_id: Replica model CQRS unique identifier.
    :param dict instance_data: Master model data.
    :return:
    """
    model_cls = ReplicaRegistry.get_model_by_cqrs_id(cqrs_id)

    if model_cls:
        if signal_type == SignalType.DELETE:
            model_cls.cqrs_delete(instance_data)

        elif signal_type == SignalType.SAVE:
            model_cls.cqrs_save(instance_data)

        else:
            logger.error('Bad signal type "{}" for CQRS_ID "{}".'.format(signal_type, cqrs_id))
