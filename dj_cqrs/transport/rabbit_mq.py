#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import logging
import time
from datetime import timedelta
from socket import gaierror
from urllib.parse import unquote, urlparse

import ujson
from django.conf import settings
from django.utils import timezone
from pika import (
    BasicProperties,
    BlockingConnection,
    ConnectionParameters,
    credentials,
    exceptions,
)
from pika.adapters.utils.connection_workflow import AMQPConnectorException

from dj_cqrs.constants import DEFAULT_DEAD_MESSAGE_TTL, SignalType
from dj_cqrs.controller import consumer
from dj_cqrs.dataclasses import TransportPayload
from dj_cqrs.delay import DelayMessage, DelayQueue
from dj_cqrs.registries import ReplicaRegistry
from dj_cqrs.transport import BaseTransport
from dj_cqrs.transport.mixins import LoggingMixin
from dj_cqrs.utils import get_delay_queue_max_size, get_messages_prefetch_count_per_worker


logger = logging.getLogger('django-cqrs')


class RabbitMQTransport(LoggingMixin, BaseTransport):
    CONSUMER_RETRY_TIMEOUT = 5
    PRODUCER_RETRIES = 1

    _producer_connection = None
    _producer_channel = None

    @classmethod
    def clean_connection(cls):
        connection = cls._producer_connection
        if connection and not connection.is_closed:
            try:
                connection.close()
            except (exceptions.StreamLostError, exceptions.ConnectionClosed, ConnectionError):
                logger.warning("Connection was closed or is closing. Skip it...")

        cls._producer_connection = None
        cls._producer_channel = None

    @classmethod
    def consume(cls, cqrs_ids=None):
        consumer_rabbit_settings = cls._get_consumer_settings()
        common_rabbit_settings = cls._get_common_settings()

        while True:
            connection = None
            try:
                delay_queue = DelayQueue(max_size=get_delay_queue_max_size())
                connection, channel, consumer_generator = cls._get_consumer_rmq_objects(
                    *(common_rabbit_settings + consumer_rabbit_settings), cqrs_ids=cqrs_ids,
                )

                for method_frame, properties, body in consumer_generator:
                    if method_frame is not None:
                        cls._consume_message(
                            channel, method_frame, properties, body, delay_queue,
                        )
                    cls._process_delay_messages(channel, delay_queue)
            except (exceptions.AMQPError,
                    exceptions.ChannelError,
                    exceptions.ReentrancyError,
                    gaierror):
                logger.error('AMQP connection error. Reconnecting...', exc_info=True)
                time.sleep(cls.CONSUMER_RETRY_TIMEOUT)
            finally:
                if connection and not connection.is_closed:
                    connection.close()

    @classmethod
    def produce(cls, payload):
        cls._produce_with_retries(payload, retries=cls.PRODUCER_RETRIES)

    @classmethod
    def _produce_with_retries(cls, payload, retries):
        try:
            rmq_settings = cls._get_common_settings()
            exchange = rmq_settings[-1]
            # Decided not to create context-manager to stay within the class
            _, channel = cls._get_producer_rmq_objects(
                *rmq_settings, signal_type=payload.signal_type,
            )

            cls._produce_message(channel, exchange, payload)
            cls.log_produced(payload)
        except (
            exceptions.AMQPError, exceptions.ChannelError, exceptions.ReentrancyError,
            AMQPConnectorException,
        ):
            logger.error("CQRS couldn't be published: pk = {0} ({1}).{2}".format(
                payload.pk, payload.cqrs_id, " Reconnect..." if retries else "",
            ))

            # in case of any error - close connection and try to reconnect
            cls.clean_connection()

            if retries:
                cls._produce_with_retries(payload, retries - 1)

    @classmethod
    def _consume_message(cls, ch, method, properties, body, delay_queue):
        try:
            dct = ujson.loads(body)
        except ValueError:
            logger.error("CQRS couldn't be parsed: {0}.".format(body))
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        required_keys = {'instance_pk', 'signal_type', 'cqrs_id', 'instance_data'}
        for key in required_keys:
            if key not in dct:
                msg = "CQRS couldn't proceed, %s isn't found in body: %s."
                logger.error(msg, key, body)
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return

        payload = TransportPayload.from_message(dct)
        cls.log_consumed(payload)

        delivery_tag = method.delivery_tag
        if payload.is_expired():
            cls._add_to_dead_letter_queue(ch, payload)
            cls._nack(ch, delivery_tag)
            return

        instance, exception = None, None
        try:
            instance = consumer.consume(payload)
        except Exception as e:
            exception = e
            logger.error("CQRS service exception", exc_info=True)

        if instance and exception is None:
            cls._ack(ch, delivery_tag, payload)
        else:
            cls._fail_message(
                ch, delivery_tag, payload, exception, delay_queue,
            )

    @classmethod
    def _fail_message(cls, channel, delivery_tag, payload, exception, delay_queue):
        cls.log_consumed_failed(payload)
        model_cls = ReplicaRegistry.get_model_by_cqrs_id(payload.cqrs_id)
        if model_cls is None:
            logger.error("Model for cqrs_id {0} is not found.".format(payload.cqrs_id))
            cls._nack(channel, delivery_tag)
            return

        if model_cls.should_retry_cqrs(payload.retries, exception):
            delay = model_cls.get_cqrs_retry_delay(payload.retries)
            cls._delay_message(channel, delivery_tag, payload, delay, delay_queue)
        else:
            cls._add_to_dead_letter_queue(channel, payload)
            cls._nack(channel, delivery_tag)

    @classmethod
    def _delay_message(cls, channel, delivery_tag, payload, delay, delay_queue):
        if delay_queue.full():
            # Memory limits handling, requeuing message with lowest ETA
            requeue_message = delay_queue.get()
            cls._requeue_message(
                channel,
                requeue_message.delivery_tag,
                requeue_message.payload,
            )

        eta = timezone.now() + timedelta(seconds=delay)
        delay_message = DelayMessage(delivery_tag, payload, eta)
        delay_queue.put(delay_message)
        cls.log_delayed(payload, delay, delay_message.eta)

    @classmethod
    def _add_to_dead_letter_queue(cls, channel, payload):
        replica_settings = settings.CQRS.get('replica', {})
        dead_message_ttl = DEFAULT_DEAD_MESSAGE_TTL
        if 'dead_message_ttl' in replica_settings:
            dead_message_ttl = replica_settings['dead_message_ttl']

        expiration = None
        if dead_message_ttl is not None:
            expiration = str(dead_message_ttl * 1000)  # milliseconds

        payload.is_dead_letter = True
        exchange = cls._get_common_settings()[-1]
        cls._produce_message(channel, exchange, payload, expiration)
        cls.log_dead_letter(payload)

    @classmethod
    def _requeue_message(cls, channel, delivery_tag, payload):
        payload.retries += 1
        payload.is_requeue = True

        cls.produce(payload)
        cls._nack(channel, delivery_tag)
        cls.log_requeued(payload)

    @classmethod
    def _process_delay_messages(cls, channel, delay_queue):
        for delay_message in delay_queue.get_ready():
            cls._requeue_message(channel, delay_message.delivery_tag, delay_message.payload)

    @classmethod
    def _produce_message(cls, channel, exchange, payload, expiration=None):
        routing_key = cls._get_produced_message_routing_key(payload)

        channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=ujson.dumps(payload.to_dict()),
            mandatory=True,
            properties=BasicProperties(
                content_type='text/plain',
                delivery_mode=2,  # make message persistent
                expiration=expiration,
            ),
        )

    @classmethod
    def _get_produced_message_routing_key(cls, payload):
        routing_key = payload.cqrs_id

        if payload.signal_type == SignalType.SYNC and payload.queue:
            routing_key = 'cqrs.{0}.{1}'.format(payload.queue, routing_key)
        elif getattr(payload, 'is_dead_letter', False):
            dead_letter_queue_name = cls._get_consumer_settings()[1]
            routing_key = 'cqrs.{0}.{1}'.format(dead_letter_queue_name, routing_key)
        elif getattr(payload, 'is_requeue', False):
            queue = cls._get_consumer_settings()[0]
            routing_key = 'cqrs.{0}.{1}'.format(queue, routing_key)

        return routing_key

    @classmethod
    def _get_consumer_rmq_objects(
        cls,
        host,
        port,
        creds,
        exchange,
        queue_name,
        dead_letter_queue_name,
        prefetch_count,
        cqrs_ids=None,
    ):
        connection = BlockingConnection(
            ConnectionParameters(host=host, port=port, credentials=creds),
        )
        channel = connection.channel()
        channel.basic_qos(prefetch_count=prefetch_count)
        cls._declare_exchange(channel, exchange)

        channel.queue_declare(queue_name, durable=True, exclusive=False)
        channel.queue_declare(dead_letter_queue_name, durable=True, exclusive=False)

        for cqrs_id, _ in ReplicaRegistry.models.items():
            if cqrs_ids and cqrs_id not in cqrs_ids:
                continue

            channel.queue_bind(exchange=exchange, queue=queue_name, routing_key=cqrs_id)

            # Every service must have specific SYNC or requeue routes
            channel.queue_bind(
                exchange=exchange,
                queue=queue_name,
                routing_key='cqrs.{0}.{1}'.format(queue_name, cqrs_id),
            )

            # Dead letter
            channel.queue_bind(
                exchange=exchange,
                queue=dead_letter_queue_name,
                routing_key='cqrs.{0}.{1}'.format(dead_letter_queue_name, cqrs_id),
            )

        delay_queue_check_timeout = 1  # seconds
        consumer_generator = channel.consume(
            queue=queue_name,
            auto_ack=False,
            exclusive=False,
            inactivity_timeout=delay_queue_check_timeout,
        )
        return connection, channel, consumer_generator

    @classmethod
    def _get_producer_rmq_objects(cls, host, port, creds, exchange, signal_type=None):
        """
        Use shared connection in case of sync mode, otherwise create new connection for each
        message
        """
        if signal_type == SignalType.SYNC:
            if cls._producer_connection is None:
                connection, channel = cls._create_connection(host, port, creds, exchange)

                cls._producer_connection = connection
                cls._producer_channel = channel

            return cls._producer_connection, cls._producer_channel
        else:
            return cls._create_connection(host, port, creds, exchange)

    @classmethod
    def _create_connection(cls, host, port, creds, exchange):
        connection = BlockingConnection(
            ConnectionParameters(
                host=host,
                port=port,
                credentials=creds,
                blocked_connection_timeout=10,
            ),
        )
        channel = connection.channel()
        channel.basic_qos(prefetch_count=get_messages_prefetch_count_per_worker())
        cls._declare_exchange(channel, exchange)

        return connection, channel

    @staticmethod
    def _declare_exchange(channel, exchange):
        channel.exchange_declare(
            exchange=exchange,
            exchange_type='topic',
            durable=True,
        )

    @staticmethod
    def _parse_url(url):
        scheme = urlparse(url).scheme
        assert scheme == 'amqp', 'Scheme must be "amqp" for RabbitMQTransport.'

        schemeless = url[len(scheme) + 3:]
        parts = urlparse('http://' + schemeless)

        return (
            unquote(parts.hostname or '') or ConnectionParameters.DEFAULT_HOST,
            parts.port or ConnectionParameters.DEFAULT_PORT,
            unquote(parts.username or '') or ConnectionParameters.DEFAULT_USERNAME,
            unquote(parts.password or '') or ConnectionParameters.DEFAULT_PASSWORD,
        )

    @classmethod
    def _get_common_settings(cls):
        if 'url' in settings.CQRS:
            host, port, user, password = cls._parse_url(settings.CQRS.get('url'))
        else:
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

    @staticmethod
    def _get_consumer_settings():
        queue_name = settings.CQRS['queue']

        replica_settings = settings.CQRS.get('replica', {})
        dead_letter_queue_name = 'dead_letter_{0}'.format(queue_name)
        if 'dead_letter_queue' in replica_settings:
            dead_letter_queue_name = replica_settings['dead_letter_queue']

        if 'consumer_prefetch_count' in settings.CQRS:
            logger.warning(
                "The 'consumer_prefetch_count' setting is ignored for RabbitMQTransport.",
            )
        prefetch_count = get_messages_prefetch_count_per_worker()

        return (
            queue_name,
            dead_letter_queue_name,
            prefetch_count,
        )

    @classmethod
    def _ack(cls, channel, delivery_tag, payload=None):
        channel.basic_ack(delivery_tag)
        if payload is not None:
            cls.log_consumed_accepted(payload)

    @classmethod
    def _nack(cls, channel, delivery_tag, payload=None):
        channel.basic_nack(delivery_tag, requeue=False)
        if payload is not None:
            cls.log_consumed_denied(payload)
