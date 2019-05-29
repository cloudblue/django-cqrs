from __future__ import unicode_literals

from dj_cqrs.factories import ReplicaFactory


def consume(payload):
    """ Consumer controller.

    :param TransportPayload payload: Consumed payload from master service.
    """
    ReplicaFactory.factory(payload.signal_type, payload.cqrs_id, payload.instance_data)
