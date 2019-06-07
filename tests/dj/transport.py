from __future__ import unicode_literals

from dj_cqrs.controller import consumer
from dj_cqrs.transport import BaseTransport


class TransportStub(BaseTransport):
    @staticmethod
    def produce(payload):
        TransportStub.consume(payload)

    @staticmethod
    def consume(payload):
        consumer.consume(payload)
