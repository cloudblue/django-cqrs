#  Copyright © 2023 Ingram Micro Inc. All rights reserved.

from datetime import datetime, timezone

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


def test_transport_payload_without_expires(mocker, settings):
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('django.utils.timezone.now', return_value=fake_now)

    settings.CQRS['master']['CQRS_MESSAGE_TTL'] = 10
    expected_expires = datetime(2020, 1, 1, second=10, tzinfo=timezone.utc)

    payload = TransportPayload.from_message({
        'signal_type': SignalType.SYNC,
        'cqrs_id': 'cqrs_id',
        'instance_data': {},
        'instance_pk': 'id',
    })

    assert payload.expires == expected_expires
