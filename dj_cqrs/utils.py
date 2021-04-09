#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from dj_cqrs.constants import DEFAULT_MESSAGE_TTL

logger = logging.getLogger('django-cqrs')


def get_expires_datetime():
    """Calculates when message should expire.

    :return: datetime instance, None if infinite
    :rtype: datetime.datetime
    """
    message_ttl = settings.CQRS.get('message_ttl', DEFAULT_MESSAGE_TTL)
    if message_ttl is None:
        # Infinite
        return

    min_message_ttl = 1
    if not isinstance(message_ttl, int) or message_ttl < min_message_ttl:
        logger.warning(
            "Settings message_ttl={} is invalid, using default {}".format(
                message_ttl, DEFAULT_MESSAGE_TTL,
            )
        )
        message_ttl = DEFAULT_MESSAGE_TTL

    return timezone.now() + timedelta(seconds=message_ttl)
