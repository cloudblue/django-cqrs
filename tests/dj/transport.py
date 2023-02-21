#  Copyright © 2023 Ingram Micro Inc. All rights reserved.

import os

from dj_cqrs.controller import consumer
from dj_cqrs.transport.base import BaseTransport
from dj_cqrs.transport.kombu import KombuTransport
from dj_cqrs.transport.rabbit_mq import RabbitMQTransport


class TransportStub(BaseTransport):
    @staticmethod
    def produce(payload):
        TransportStub.consume(payload)

    @staticmethod
    def consume(payload=None):
        if payload:
            return consumer.consume(payload)


class RabbitMQTransportWithEvents(RabbitMQTransport):
    @staticmethod
    def log_consumed(payload):
        from tests.dj_replica.models import Event
        Event.objects.create(
            pid=os.getpid(),
            cqrs_id=payload.cqrs_id,
            cqrs_revision=int(payload.instance_data['cqrs_revision']),
        )


class KombuTransportWithEvents(KombuTransport):
    @staticmethod
    def log_consumed(payload):
        from tests.dj_replica.models import Event
        Event.objects.create(
            pid=os.getpid(),
            cqrs_id=payload.cqrs_id,
            cqrs_revision=int(payload.instance_data['cqrs_revision']),
        )
