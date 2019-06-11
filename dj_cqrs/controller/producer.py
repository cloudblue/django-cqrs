from __future__ import unicode_literals

from dj_cqrs.transport import current_transport


def produce(payload):
    """ Producer controller.

    :param dj_cqrs.dataclasses.TransportPayload payload: TransportPayload.
    """
    current_transport.produce(payload)
