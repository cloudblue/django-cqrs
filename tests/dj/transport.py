from __future__ import unicode_literals

from django.dispatch import Signal
from dj_cqrs.transport import BaseTransport


publish_signal = consume_signal = Signal(providing_args=['payload'])


class TransportStub(BaseTransport):
    @staticmethod
    def publish(payload):
        publish_signal.send(None, payload=payload)
        TransportStub.consume(payload)

    @staticmethod
    def consume(payload):
        consume_signal.send(None, payload=payload)
