#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

from django.conf import settings
from django.utils.module_loading import import_string

from dj_cqrs.transport.base import BaseTransport
from dj_cqrs.transport.kombu import KombuTransport
from dj_cqrs.transport.rabbit_mq import RabbitMQTransport


transport_cls_location = getattr(settings, 'CQRS', {}) \
    .get('transport')
if not transport_cls_location:
    raise AttributeError('CQRS transport is not set.')

try:
    current_transport = import_string(transport_cls_location)

    if not issubclass(current_transport, BaseTransport):
        raise ValueError

except (ImportError, ValueError):
    raise ImportError('Bad CQRS transport class.')


__all__ = [BaseTransport, KombuTransport, RabbitMQTransport, current_transport]
