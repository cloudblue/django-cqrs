from __future__ import unicode_literals

import logging
import time

import ujson
from django.conf import settings
from pika import exceptions, BasicProperties, BlockingConnection, ConnectionParameters, credentials

from dj_cqrs.controller import consumer
from dj_cqrs.dataclasses import TransportPayload
from dj_cqrs.registries import ReplicaRegistry
from dj_cqrs.transport import BaseTransport

logger = logging.getLogger()


class RabbitMQTransport(BaseTransport):
    @classmethod
    def consume(cls):
        queue_name = settings.CQRS['queue']
        rabbit_settings = cls._get_settings() + (queue_name,)

        while True:
            try:
                connection, channel = cls._get_consumer_rmq_objects(*rabbit_settings)
                channel.basic_consume(
                    queue=queue_name, on_message_callback=cls._consume_message, auto_ack=True,
                )
                channel.start_consuming()
            except exceptions.AMQPError:
                time.sleep(2)
                logger.error('AMQP connection error... Reconnecting.')
                continue

    @classmethod
    def produce(cls, payload):
        rmq_settings = cls._get_settings()
        exchange = rmq_settings[-1]

        try:
            # Decided not to create context-manager to stay within the class
            connection, channel = cls._get_producer_rmq_objects(*rmq_settings)

            cls._publish_message(channel, exchange, payload)
            logger.info('CQRS is published: pk = {} ({}).'.format(payload.pk, payload.cqrs_id))

            connection.close()
        except exceptions.AMQPError:
            logger.error("CQRS couldn't be published: pk = {} ({}).".format(
                payload.pk, payload.cqrs_id,
            ))

    @staticmethod
    def _consume_message(*args):
        dct = ujson.loads(args[-1])
        payload = TransportPayload(dct['signal_type'], dct['cqrs_id'], dct['instance_data'])
        consumer.consume(payload)

    @classmethod
    def _publish_message(cls, channel, exchange, payload):
        routing_key = payload.cqrs_id

        channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=ujson.dumps(payload.to_dict()),
            mandatory=True,
            properties=BasicProperties(content_type='text/plain', delivery_mode=2)
        )

    @classmethod
    def _get_consumer_rmq_objects(cls, host, port, creds, exchange, queue_name):
        connection = BlockingConnection(
            ConnectionParameters(host=host, port=port, credentials=creds),
        )
        channel = connection.channel()
        channel.exchange_declare(exchange=exchange, exchange_type='topic')
        channel.queue_declare(queue_name, durable=True, exclusive=False)

        for cqrs_id, replica_model in ReplicaRegistry.models.items():
            channel.queue_bind(exchange=exchange, queue=queue_name, routing_key=cqrs_id)

        return connection, channel

    @classmethod
    def _get_producer_rmq_objects(cls, host, port, creds, exchange):
        connection = BlockingConnection(
            ConnectionParameters(
                host=host, port=port, credentials=creds,
                blocked_connection_timeout=10,
            ),
        )
        channel = connection.channel()
        channel.exchange_declare(
            exchange=exchange,
            exchange_type='topic',
        )
        return connection, channel

    @staticmethod
    def _get_settings():
        host = settings.CQRS.get('host', ConnectionParameters.DEFAULT_HOST)
        port = settings.CQRS.get('port', ConnectionParameters.DEFAULT_PORT)
        user = settings.CQRS.get('user', ConnectionParameters.DEFAULT_USERNAME)
        password = settings.CQRS.get('password', ConnectionParameters.DEFAULT_PASSWORD)
        exchange = settings.CQRS.get('exchange', 'cqrs')
        return (
            host,
            port,
            credentials.PlainCredentials(user, password, erase_on_connect=True),
            exchange,
        )
