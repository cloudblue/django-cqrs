from __future__ import unicode_literals

from django.conf import settings
from django.utils.module_loading import import_string

from dj_cqrs.transport.base import BaseTransport


transport_cls_location = getattr(settings, 'CQRS', {}) \
    .get('transport')
if not transport_cls_location:
    raise AttributeError('CQRS transport is not setup.')

try:
    current_transport = import_string(transport_cls_location)

    if not issubclass(current_transport, BaseTransport):
        raise ValueError

except (ImportError, ValueError):
    raise ImportError('Bad CQRS transport class.')
