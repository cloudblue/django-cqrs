from __future__ import unicode_literals

from importlib import import_module
from django.conf import settings


class BaseTransport(object):
    current = None

    @staticmethod
    def publish(payload):
        raise NotImplementedError

    @staticmethod
    def consume(payload):
        raise NotImplementedError


def _load_transport_class(cls_string):
    split_str = cls_string.split('.')
    return getattr(import_module('.'.join(split_str[:-1])), split_str[-1])


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
