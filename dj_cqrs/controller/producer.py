#  Copyright © 2025 CloudBlue Inc. All rights reserved.

from dj_cqrs.transport import current_transport


def produce(payload):
    """Producer controller.

    :param dj_cqrs.dataclasses.TransportPayload payload: TransportPayload.
    """
    current_transport.produce(payload)
