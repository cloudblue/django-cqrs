from __future__ import unicode_literals

from importlib import import_module

from django.conf import settings

from dj_cqrs.transport.base import BaseTransport


def _load_transport_class(cls_string):
    split_str = cls_string.split('.')
    module_path, cls_name = '.'.join(split_str[:-1]), split_str[-1]
    return getattr(import_module(module_path), cls_name)


transport_cls_location = getattr(settings, 'CQRS', {}) \
    .get('transport')
if not transport_cls_location:
    raise AttributeError('CQRS transport is not setup.')

try:
    current_transport = _load_transport_class(transport_cls_location)
    if not issubclass(current_transport, BaseTransport):
        raise ValueError
except (ImportError, ValueError):
    raise ImportError('Bad CQRS transport class.')
