from __future__ import unicode_literals


from django.core.management.base import BaseCommand
from dj_cqrs.transport.rabbit_mq import RabbitMQTransport


class Command(BaseCommand):
    help = 'Starts CQRS worker, which consumes messages from message queue.'

    def handle(self, *args, **options):
        RabbitMQTransport.consume()
