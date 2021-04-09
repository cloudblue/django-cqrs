#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from dj_cqrs.constants import SignalType
from dj_cqrs.dataclasses import TransportPayload


def test_transport_payload_infinite_expires():
    payload = TransportPayload.from_message({
        'signal_type': SignalType.SYNC,
        'cqrs_id': 'cqrs_id',
        'instance_data': {},
        'instance_pk': 'id',
        'expires': None,
    })

    assert payload.expires is None
