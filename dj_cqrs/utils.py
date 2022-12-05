#  Copyright © 2022 Ingram Micro Inc. All rights reserved.

import logging
from datetime import date, datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.utils import timezone


logger = logging.getLogger('django-cqrs')


def get_message_expiration_dt(message_ttl=None):
    """Calculates when message should expire.

    :param int or None message_ttl:
    :return: Expiration datetime or None if infinite
    :rtype: datetime.datetime or None
    """
    message_ttl = message_ttl or settings.CQRS['master']['CQRS_MESSAGE_TTL']
    if message_ttl is None:
        # Infinite
        return

    return timezone.now() + timedelta(seconds=message_ttl)


def get_delay_queue_max_size():
    """Returns max allowed number of "waiting" messages in the delay queue.

    :return: Positive integer number or None if infinite
    :rtype: int
    """
    if 'replica' not in settings.CQRS:
        return None

    return settings.CQRS['replica']['delay_queue_max_size']


def get_messages_prefetch_count_per_worker():
    """Returns max allowed number of unacked messages, that can be consumed by a single worker.

    :return: Positive integer number or 0 if infinite
    :rtype: int
    """
    delay_queue_max_size = get_delay_queue_max_size()
    if delay_queue_max_size is None:
        # Infinite
        return 0

    return delay_queue_max_size + 1


def get_json_valid_value(value):
    return str(value) if isinstance(value, (date, datetime, UUID)) else value
