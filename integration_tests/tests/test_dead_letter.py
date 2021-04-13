#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import json

import pytest
from pika import BlockingConnection, URLParameters

from dj_cqrs.transport import current_transport
from dj_cqrs.transport.rabbit_mq import RabbitMQTransport
from integration_tests.tests.utils import transport_delay
from tests.dj_master.models import FailModel


@pytest.mark.django_db(transaction=True)
def test_add_to_dead_letter(settings, replica_cursor):
    if current_transport is not RabbitMQTransport:
        pytest.skip("Dead letter queue is implemented only for RabbitMQTransport.")

    connection = BlockingConnection(
        parameters=URLParameters(settings.CQRS['url']),
    )
    channel = connection.channel()
    channel.queue_purge('dead_letter_replica')

    master_instance = FailModel.cqrs.create()
    transport_delay(5)

    queue = channel.queue_declare('replica', durable=True, exclusive=False)
    assert queue.method.message_count == 0

    dead_queue = channel.queue_declare('dead_letter_replica', durable=True, exclusive=False)
    assert dead_queue.method.message_count == 1

    consumer_generator = channel.consume(
        queue=dead_queue.method.queue,
        auto_ack=True,
        exclusive=False,
    )
    *_, body = next(consumer_generator)
    dead_letter = json.loads(body)

    assert dead_letter['instance_pk'] == master_instance.pk
    assert dead_letter['retries'] == 2


@pytest.mark.django_db(transaction=True)
def test_dead_letter_expire(settings, replica_cursor):
    if current_transport is not RabbitMQTransport:
        pytest.skip("Dead letter queue is implemented only for RabbitMQTransport.")

    connection = BlockingConnection(
        parameters=URLParameters(settings.CQRS['url']),
    )
    channel = connection.channel()
    channel.queue_purge('dead_letter_replica')

    FailModel.cqrs.create()
    transport_delay(5)

    dead_queue = channel.queue_declare('dead_letter_replica', durable=True, exclusive=False)
    assert dead_queue.method.message_count == 1

    transport_delay(5)

    dead_queue = channel.queue_declare('dead_letter_replica', durable=True, exclusive=False)
    assert dead_queue.method.message_count == 0
