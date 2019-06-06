from __future__ import unicode_literals

import logging
import time
import threading

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
        rabbit_settings = cls._get_settings() + (settings.CQRS['queue'],)
        t = RabbitMQConsumerThread(*rabbit_settings)
        t.start()
        return t

    @classmethod
    def produce(cls, payload):
        rmq_settings = cls._get_settings()
        exchange = rmq_settings[-1]

        try:
            # Decided not to create context-manager to stay within the class
            connection, channel = cls._get_producer_rmq_objects(*rmq_settings)
            is_published = cls._publish_message(channel, exchange, payload)

            if is_published:
                logger.info('CQRS is published: pk = {} ({}).'.format(payload.pk, payload.cqrs_id))
            else:
                raise exceptions.AMQPError

            connection.close()
        except exceptions.AMQPError:
            logger.error("CQRS couldn't be published: pk = {} ({}).".format(
                payload.pk, payload.cqrs_id,
            ))

    @classmethod
    def _publish_message(cls, channel, exchange, payload):
        routing_key = payload.cqrs_id

        return channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=ujson.dumps(payload.to_dict()),
            mandatory=True,
            properties=BasicProperties(
                content_type='text/plain', delivery_mode=2,
            )
        )

    @classmethod
    def _get_producer_rmq_objects(cls, host, port, creds, exchange):
        connection = BlockingConnection(
            ConnectionParameters(
                host=host, port=port, credentials=creds,
                blocked_connection_timeout=2.0,
            ),
        )
        channel = connection.channel()
        channel.exchange_declare(
            exchange=exchange,
            exchange_type='topic',
        )
        channel.confirm_delivery()

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


class RabbitMQConsumerThread(threading.Thread):
    def __init__(self, *args):
        super(RabbitMQConsumerThread, self).__init__()
        self._rabbit_settings = args

    def run(self):
        exchange, queue_name = self._rabbit_settings[-2], self._rabbit_settings[-1]

        while True:
            try:
                connection, channel = self._get_consumer_rmq_objects()

                def callback(ch, method, properties, body):
                    dct = ujson.loads(body)
                    payload = TransportPayload(dct['signal_type'], dct['cqrs_id'],
                                               dct['instance_data'])
                    consumer.consume(payload)

                channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
                channel.start_consuming()
            except exceptions.AMQPError:
                if self.stopped():
                    return

                time.sleep(2)
                logger.error('AMQP connection error... Reconnecting.')
                continue

    def _get_consumer_rmq_objects(self):
        host, port, creds, exchange, queue_name = self._rabbit_settings

        connection = BlockingConnection(
            ConnectionParameters(host=host, port=port, credentials=creds),
        )
        channel = connection.channel()
        channel.exchange_declare(exchange=exchange, exchange_type='topic')
        channel.queue_declare(queue_name, durable=True, exclusive=False)

        for cqrs_id, replica_model in ReplicaRegistry.models.items():
            channel.queue_bind(exchange=exchange, queue=queue_name, routing_key=cqrs_id)

        return connection, channel
