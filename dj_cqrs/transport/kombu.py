#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import logging

import ujson
from django.conf import settings
from kombu import Connection, Exchange, Producer, Queue
from kombu.exceptions import KombuError
from kombu.mixins import ConsumerMixin


from dj_cqrs.constants import SignalType
from dj_cqrs.controller import consumer
from dj_cqrs.dataclasses import TransportPayload
from dj_cqrs.registries import ReplicaRegistry
from dj_cqrs.transport import BaseTransport
from dj_cqrs.transport.mixins import LoggingMixin

logger = logging.getLogger('django-cqrs')


class _KombuConsumer(ConsumerMixin):

    def __init__(self, url, exchange_name, queue_name, prefetch_count, callback):
        self.connection = Connection(url)
        self.exchange = Exchange(
            exchange_name,
            type='topic',
            durable=True,
        )
        self.queue_name = queue_name
        self.prefetch_count = prefetch_count
        self.callback = callback
        self.queues = []
        self._init_queues()

    def _init_queues(self):
        channel = self.connection.channel()
        for cqrs_id in ReplicaRegistry.models.keys():
            q = Queue(
                self.queue_name,
                exchange=self.exchange,
                routing_key=cqrs_id,
            )
            q.maybe_bind(channel)
            q.declare()
            self.queues.append(q)

            sync_q = Queue(
                self.queue_name,
                exchange=self.exchange,
                routing_key='cqrs.{}.{}'.format(self.queue_name, cqrs_id),
            )
            sync_q.maybe_bind(channel)
            sync_q.declare()
            self.queues.append(sync_q)

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(
                queues=self.queues,
                callbacks=[self.callback],
                prefetch_count=self.prefetch_count,
                auto_declare=True,
            ),
        ]


class KombuTransport(LoggingMixin, BaseTransport):
    CONSUMER_RETRY_TIMEOUT = 5

    @classmethod
    def consume(cls):
        queue_name, prefetch_count = cls._get_consumer_settings()
        url, exchange_name = cls._get_common_settings()

        consumer = _KombuConsumer(
            url,
            exchange_name,
            queue_name,
            prefetch_count,
            cls._consume_message,
        )
        consumer.run()

    @classmethod
    def produce(cls, payload):
        url, exchange_name = cls._get_common_settings()

        connection = None
        try:
            # Decided not to create context-manager to stay within the class
            connection, channel = cls._get_producer_kombu_objects(url, exchange_name)
            exchange = cls._create_exchange(exchange_name)
            cls._produce_message(channel, exchange, payload)
            cls.log_produced(payload)
        except KombuError:
            logger.error("CQRS couldn't be published: pk = {} ({}).".format(
                payload.pk, payload.cqrs_id,
            ))
        finally:
            if connection:
                connection.close()

    @classmethod
    def _consume_message(cls, body, message):
        try:
            dct = ujson.loads(body)
            for key in ('signal_type', 'cqrs_id', 'instance_data'):
                if key not in dct:
                    raise ValueError

            if 'instance_pk' not in dct:
                logger.warning('CQRS deprecated package structure.')

        except ValueError:
            logger.error("CQRS couldn't be parsed: {}.".format(body))
            message.reject()
            return

        payload = TransportPayload(
            dct['signal_type'], dct['cqrs_id'], dct['instance_data'], dct.get('instance_pk'),
            previous_data=dct.get('previous_data'),
        )

        cls.log_consumed(payload)
        instance = consumer.consume(payload)

        if instance:
            message.ack()
            cls.log_consumed_accepted(payload)
        else:
            message.reject()
            cls.log_consumed_denied(payload)

    @classmethod
    def _produce_message(cls, channel, exchange, payload):
        routing_key = cls._get_produced_message_routing_key(payload)
        producer = Producer(
            channel,
            exchange=exchange,
            auto_declare=True,
        )
        producer.publish(
            ujson.dumps(payload.to_dict()),
            routing_key=routing_key,
            mandatory=True,
            content_type='text/plain',
            delivery_mode=2,
        )

    @staticmethod
    def _get_produced_message_routing_key(payload):
        routing_key = payload.cqrs_id

        if payload.signal_type == SignalType.SYNC and payload.queue:
            routing_key = 'cqrs.{}.{}'.format(payload.queue, routing_key)

        return routing_key

    @classmethod
    def _get_producer_kombu_objects(cls, url, exchange_name):
        connection = Connection(url)
        channel = connection.channel()
        return connection, channel

    @staticmethod
    def _create_exchange(exchange_name):
        return Exchange(
            exchange_name,
            type='topic',
            durable=True,
        )

    @staticmethod
    def _get_common_settings():
        url = settings.CQRS.get('url', 'amqp://localhost')
        exchange = settings.CQRS.get('exchange', 'cqrs')
        return (
            url,
            exchange,
        )

    @staticmethod
    def _get_consumer_settings():
        queue_name = settings.CQRS['queue']
        consumer_prefetch_count = settings.CQRS.get('consumer_prefetch_count', 10)
        return (
            queue_name,
            consumer_prefetch_count,
        )
