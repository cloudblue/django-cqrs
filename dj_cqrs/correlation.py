#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from django.conf import settings


_correlation_function = getattr(settings, 'CQRS', {}).get('master', {}).get('correlation_function')
if _correlation_function and (not callable(_correlation_function)):
    raise AttributeError('CQRS correlation_function must be callable.')


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
    if _correlation_function:
        return _correlation_function(signal_type, cqrs_id, instance_pk, queue)
