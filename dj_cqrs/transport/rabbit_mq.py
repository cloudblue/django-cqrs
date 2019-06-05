from __future__ import unicode_literals

import logging

from django.conf import settings
from pika import exceptions, BasicProperties, BlockingConnection, ConnectionParameters, credentials

from dj_cqrs.transport import BaseTransport


logger = logging.getLogger()


class RabbitMQTransport(BaseTransport):
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
