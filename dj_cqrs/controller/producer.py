from __future__ import unicode_literals

from dj_cqrs.dataclasses import TransportPayload
from dj_cqrs.transport import current_transport


def produce(signal_type, cqrs_id, instance_data, instance_pk):
    """ Producer controller.

    :param dj_cqrs.constants.SignalType signal_type: Produced signal type.
    :param str cqrs_id: Master model CQRS unique identifier.
    :param dict instance_data: Master model data.
    :param instance_pk: Master model instance pk.
    """
    payload = TransportPayload(signal_type, cqrs_id, instance_data, instance_pk)
    current_transport.produce(payload)
