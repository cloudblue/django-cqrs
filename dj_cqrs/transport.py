from __future__ import unicode_literals

from importlib import import_module

from django.conf import settings


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


def _load_transport_class(cls_string):
    split_str = cls_string.split('.')
    module_path, cls_name = '.'.join(split_str[:-1]), split_str[-1]
    return getattr(import_module(module_path), cls_name)


transport_cls_location = getattr(settings, 'CQRS', {}) \
    .get('transport', {}) \
    .get('class')
if not transport_cls_location:
    raise AttributeError('CQRS transport is not setup.')

try:
    current_transport = _load_transport_class(transport_cls_location)
    if not issubclass(current_transport, BaseTransport):
        raise ValueError
except (ImportError, ValueError):
    raise ImportError('Bad CQRS transport class.')
