#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import psycopg2
import pytest
from pika import BlockingConnection, URLParameters

from integration_tests.tests.utils import REPLICA_TABLES

from dj_cqrs.transport import current_transport
from dj_cqrs.transport.rabbit_mq import RabbitMQTransport


@pytest.fixture
def replica_cursor():
    connection = psycopg2.connect(host='postgres', database='replica', user='user', password='pswd')

    # That setting is extremely important for table truncations
    connection.set_isolation_level(0)

    cursor = connection.cursor()
    for table in REPLICA_TABLES:
        cursor.execute('TRUNCATE TABLE {};'.format(table))

    yield cursor

    cursor.close()
    connection.close()


@pytest.fixture
def clean_rabbit_transport_connection():
    current_transport.clean_connection()

    yield


@pytest.fixture
def replica_channel(settings):
    if current_transport is not RabbitMQTransport:
        pytest.skip("Replica channel is implemented only for RabbitMQTransport.")

    connection = BlockingConnection(
        parameters=URLParameters(settings.CQRS['url']),
    )
    rabbit_mq_channel = connection.channel()

    rabbit_mq_channel.queue_purge('replica')
    rabbit_mq_channel.queue_purge('dead_letter_replica')

    yield rabbit_mq_channel

    connection.close()
