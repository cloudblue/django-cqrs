from dj_cqrs.transport import BaseTransport


class TransportMock(BaseTransport):
    @staticmethod
    def produce(payload):
        return TransportMock.consume(payload)

    @staticmethod
    def consume(payload):
        return payload
