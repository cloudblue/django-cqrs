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

        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        raise NotImplementedError

    @staticmethod
    def consume(*args, **kwargs):
        """Receive data from master model."""
        raise NotImplementedError

    @staticmethod
    def clean_connection(*args, **kwargs):
        """Clean transport connection. Here you can close all connections that you have"""
        raise NotImplementedError
