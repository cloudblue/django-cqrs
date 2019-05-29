from __future__ import unicode_literals

from dj_cqrs.dataclasses import TransportPayload
from dj_cqrs.transport import current_transport


def produce(signal_type, cqrs_id, instance_data):
    """ Producer controller.

    :param dj_cqrs.constants.SignalType signal_type: Produced signal type.
    :param str cqrs_id: Master model CQRS unique identifier.
    :param dict instance_data: Master model data.
    """
    payload = TransportPayload(signal_type=signal_type, cqrs_id=cqrs_id, instance_data=instance_data)
    current_transport.produce(payload)
