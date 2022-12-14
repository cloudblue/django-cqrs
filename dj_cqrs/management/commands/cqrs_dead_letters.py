#  Copyright © 2022 Ingram Micro Inc. All rights reserved.

import ujson
from django.core.management.base import BaseCommand, CommandError

from dj_cqrs.constants import DEFAULT_MASTER_MESSAGE_TTL
from dj_cqrs.dataclasses import TransportPayload
from dj_cqrs.registries import ReplicaRegistry
from dj_cqrs.transport import current_transport
from dj_cqrs.transport.rabbit_mq import RabbitMQTransport
from dj_cqrs.utils import get_message_expiration_dt


class RabbitMQTransportService(RabbitMQTransport):

    @classmethod
    def get_consumer_settings(cls):
        return cls._get_consumer_settings()

    @classmethod
    def get_common_settings(cls):
        return cls._get_common_settings()

    @classmethod
    def create_connection(cls, host, port, creds, exchange):
        return cls._create_connection(host, port, creds, exchange)

    @classmethod
    def declare_queue(cls, channel, queue_name):
        return channel.queue_declare(queue_name, durable=True, exclusive=False)

    @classmethod
    def nack(cls, channel, delivery_tag, payload=None):
        return cls._nack(channel, delivery_tag, payload)


class Command(BaseCommand):
    help = 'CQRS dead letters queue management commands'

    def add_arguments(self, parser):
        command = parser.add_subparsers(dest='command')
        command.required = True
        command.add_parser('retry', help='Retry all dead letters.')
        command.add_parser('dump', help='Dumps all dead letter to stdout.')
        command.add_parser('purge', help='Removes all dead letters.')

    def handle(self, *args, **options):
        self.check_transport()
        channel, connection = self.init_broker()

        queue_name, dead_letter_queue_name, *_ = RabbitMQTransportService.get_consumer_settings()
        dead_letters_queue = RabbitMQTransportService.declare_queue(
            channel, dead_letter_queue_name,
        )
        dead_letters_count = dead_letters_queue.method.message_count
        consumer_generator = channel.consume(
            queue=dead_letter_queue_name,
            auto_ack=False,
            exclusive=False,
        )

        command = options['command']
        if command == 'retry':
            self.handle_retry(channel, consumer_generator, dead_letters_count)
        elif command == 'dump':
            self.handle_dump(consumer_generator, dead_letters_count)
        elif command == 'purge':
            self.handle_purge(channel, dead_letter_queue_name, dead_letters_count)

        if not connection.is_closed:
            connection.close()

    def check_transport(self):
        if not issubclass(current_transport, RabbitMQTransport):
            raise CommandError("Dead letters commands available only for RabbitMQTransport.")

    def init_broker(self):
        host, port, creds, exchange = RabbitMQTransportService.get_common_settings()
        connection, channel = RabbitMQTransportService.create_connection(
            host, port, creds, exchange,
        )

        queue_name, dead_letter_queue_name, *_ = RabbitMQTransportService.get_consumer_settings()
        RabbitMQTransportService.declare_queue(channel, queue_name)
        RabbitMQTransportService.declare_queue(channel, dead_letter_queue_name)
        for cqrs_id, _ in ReplicaRegistry.models.items():
            channel.queue_bind(exchange=exchange, queue=queue_name, routing_key=cqrs_id)

            # Every service must have specific SYNC or requeue routes
            channel.queue_bind(
                exchange=exchange,
                queue=queue_name,
                routing_key='cqrs.{0}.{1}'.format(queue_name, cqrs_id),
            )

        return channel, connection

    def handle_retry(self, channel, consumer_generator, dead_letters_count):
        self.stdout.write("Total dead letters: {0}".format(dead_letters_count))
        for i in range(1, dead_letters_count + 1):
            self.stdout.write("Retrying: {0}/{1}".format(i, dead_letters_count))
            method_frame, properties, body = next(consumer_generator)

            dct = ujson.loads(body)
            dct['retries'] = 0
            if dct.get('expires'):
                # Message could expire already
                expires = get_message_expiration_dt(DEFAULT_MASTER_MESSAGE_TTL)
                dct['expires'] = expires.replace(microsecond=0).isoformat()
            payload = TransportPayload.from_message(dct)
            payload.is_requeue = True

            RabbitMQTransportService.produce(payload)
            message = ujson.dumps(dct)
            self.stdout.write(message)

            RabbitMQTransportService.nack(channel, method_frame.delivery_tag)

    def handle_dump(self, consumer_generator, dead_letters_count):
        for _ in range(1, dead_letters_count + 1):
            *_, body = next(consumer_generator)
            self.stdout.write(body.decode('utf-8'))

    def handle_purge(self, channel, dead_letter_queue_name, dead_letter_count):
        self.stdout.write("Total dead letters: {0}".format(dead_letter_count))
        if dead_letter_count > 0:
            channel.queue_purge(dead_letter_queue_name)
            self.stdout.write("Purged")
