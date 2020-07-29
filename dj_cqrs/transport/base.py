#  Copyright © 2020 Ingram Micro Inc. All rights reserved.


class BaseTransport:
    """
    CQRS pattern can be implemented over any transport (AMQP, HTTP, etc.)
    All transports need to inherit from this base class.
    Transport must be set in Django settings:

    .. code-block:: python

        CQRS = {
            'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
        }
    """

    consumers = {}

    @staticmethod
    def produce(payload):
        """
        Send data from master model to replicas.

        :param payload: Transport payload from master model.
        :type payload: dj_cqrs.dataclasses.TransportPayload
        """
        raise NotImplementedError

    @staticmethod
    def consume(*args, **kwargs):
        """Receive data from master model."""
        raise NotImplementedError
