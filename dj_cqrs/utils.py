#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from dj_cqrs.constants import DEFAULT_CQRS_MESSAGE_TTL

logger = logging.getLogger('django-cqrs')


def get_expires_datetime():
    """Calculates when message should expire.

    :return: datetime instance, None if infinite
    :rtype: datetime.datetime
    """
    master_settings = settings.CQRS.get('master', {})
    if 'CQRS_MESSAGE_TTL' in master_settings and master_settings['CQRS_MESSAGE_TTL'] is None:
        # Infinite
        return

    min_message_ttl = 1
    message_ttl = master_settings.get('CQRS_MESSAGE_TTL', DEFAULT_CQRS_MESSAGE_TTL)
    if not isinstance(message_ttl, int) or message_ttl < min_message_ttl:
        logger.warning(
            "Settings CQRS_MESSAGE_TTL=%s is invalid, using default %s.",
            message_ttl, DEFAULT_CQRS_MESSAGE_TTL,
        )
        message_ttl = DEFAULT_CQRS_MESSAGE_TTL

    return timezone.now() + timedelta(seconds=message_ttl)
