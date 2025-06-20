#  Copyright © 2025 CloudBlue. All rights reserved.

from dj_cqrs.transport import BaseTransport


class TransportMock(BaseTransport):
    @staticmethod
    def produce(payload):
        return TransportMock.consume(payload)

    @staticmethod
    def consume(payload=None, **kwargs):
        return payload
