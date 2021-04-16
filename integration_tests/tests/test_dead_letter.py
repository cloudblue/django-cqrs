#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import json

import pytest

from integration_tests.tests.utils import transport_delay
from tests.dj_master.models import FailModel


@pytest.mark.django_db(transaction=True)
def test_add_to_dead_letter(settings, replica_cursor, replica_channel):
    master_instance = FailModel.cqrs.create()
    transport_delay(5)

    queue = replica_channel.queue_declare('replica', durable=True, exclusive=False)
    assert queue.method.message_count == 0

    dead_queue = replica_channel.queue_declare(
        'dead_letter_replica', durable=True, exclusive=False,
    )
    assert dead_queue.method.message_count == 1

    consumer_generator = replica_channel.consume(
        queue=dead_queue.method.queue,
        auto_ack=True,
        exclusive=False,
    )
    *_, body = next(consumer_generator)
    dead_letter = json.loads(body)

    assert dead_letter['instance_pk'] == master_instance.pk
    assert dead_letter['retries'] == 2


@pytest.mark.django_db(transaction=True)
def test_dead_letter_expire(settings, replica_cursor, replica_channel):
    FailModel.cqrs.create()
    transport_delay(5)

    dead_queue = replica_channel.queue_declare(
        'dead_letter_replica', durable=True, exclusive=False,
    )
    assert dead_queue.method.message_count == 1

    transport_delay(5)

    dead_queue = replica_channel.queue_declare(
        'dead_letter_replica', durable=True, exclusive=False,
    )
    assert dead_queue.method.message_count == 0
