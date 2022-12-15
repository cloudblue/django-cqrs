#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from django.conf import settings
from django.utils.module_loading import import_string

from dj_cqrs.transport.base import BaseTransport
from dj_cqrs.transport.kombu import KombuTransport
from dj_cqrs.transport.rabbit_mq import RabbitMQTransport


try:
    current_transport = import_string(settings.CQRS['transport'])
except (AttributeError, ImportError, KeyError):
    current_transport = None


__all__ = ['BaseTransport', 'KombuTransport', 'RabbitMQTransport', current_transport]
