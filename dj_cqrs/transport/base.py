from __future__ import unicode_literals


class BaseTransport(object):
    """
    CQRS pattern can be implemented over any transport (AMQP, HTTP, etc.)
    All transports need to inherit from this base class.
    Transport must be set in Django settings:
        CQRS = {
            'transport': {
                'class': 'tests.dj.transport.TransportStub',
            },
        }
    """
    consumers = {}

    @staticmethod
    def produce(payload):
        """ Send data from master model to replicas.

        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        raise NotImplementedError

    @staticmethod
    def consume(*args, **kwargs):
        raise NotImplementedError
