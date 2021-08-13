#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from django.conf import settings


def get_correlation_id(signal_type, cqrs_id, instance_pk, queue):
    """
    :param signal_type: Type of the signal for this message.
    :type signal_type: dj_cqrs.constants.SignalType
    :param cqrs_id: The unique CQRS identifier of the model.
    :type cqrs_id: str
    :param instance_pk: Primary key of the instance.
    :param queue: Queue to synchronize, defaults to None
    :type queue: str, optional
    """
    correlation_func = settings.CQRS.get('master', {}).get('correlation_function')
    if correlation_func:
        return correlation_func(signal_type, cqrs_id, instance_pk, queue)
