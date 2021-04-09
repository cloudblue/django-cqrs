#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import logging
from datetime import datetime, timedelta, timezone

from django.conf import settings


logger = logging.getLogger('django-cqrs')


def get_expires_datetime():
    """Calculates when message should expire.

    :return: datetime instance, None if infinite
    :rtype: datetime
    """
    default_message_ttl = 86400  # 1 day
    message_ttl = settings.CQRS.get('message_ttl', default_message_ttl)
    if message_ttl is None:
        # Infinite
        return

    min_message_ttl = 1
    if not isinstance(message_ttl, int) or message_ttl < min_message_ttl:
        logger.warning(
            "Settings message_ttl={} is invalid, using default {}".format(
                message_ttl, default_message_ttl,
            )
        )
        message_ttl = default_message_ttl

    return utc_now() + timedelta(seconds=message_ttl)


def utc_now():
    """
    :return: datetime instance with UTC timezone info.
    :rtype: datetime
    """
    return datetime.now(tz=timezone.utc)
