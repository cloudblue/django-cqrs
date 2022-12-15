#  Copyright © 2022 Ingram Micro Inc. All rights reserved.

from dateutil.parser import parse as dateutil_parse
from django.utils import timezone

from dj_cqrs.correlation import get_correlation_id
from dj_cqrs.utils import get_json_valid_value, get_message_expiration_dt


class TransportPayload:
    """Transport message payload.

    :param signal_type: Type of the signal for this message.
    :type signal_type: dj_cqrs.constants.SignalType
    :param cqrs_id: The unique CQRS identifier of the model.
    :type cqrs_id: str
    :param instance_data: Serialized data of the instance that
                            generates the event.
    :type instance_data: dict
    :param instance_pk: Primary key of the instance.
    :param queue: Queue to synchronize, defaults to None.
    :type queue: str, optional
    :param previous_data: Previous values for fields tracked for changes,
                                defaults to None.
    :type previous_data: dict, optional
    :param correlation_id: Correlation ID of process, where this payload is used.
    :type correlation_id: str, optional
    :param retries: Current number of message retries.
    :type retries: int, optional
    :param expires: Message expiration datetime, infinite if None
    :type expires: datetime, optional
    :param meta: Payload metadata
    :type meta: dict, optional
    """

    def __init__(
        self,
        signal_type,
        cqrs_id,
        instance_data,
        instance_pk,
        queue=None,
        previous_data=None,
        correlation_id=None,
        expires=None,
        retries=0,
        meta=None,
    ):
        self.__signal_type = signal_type
        self.__cqrs_id = cqrs_id
        self.__instance_data = instance_data
        self.__instance_pk = instance_pk
        self.__queue = queue
        self.__previous_data = previous_data
        self.__meta = meta

        if correlation_id:
            self.__correlation_id = correlation_id
        else:
            self.__correlation_id = get_correlation_id(signal_type, cqrs_id, instance_pk, queue)

        self.__expires = expires
        self.__retries = retries

    @classmethod
    def from_message(cls, dct):
        """Builds payload from message data.

        :param dct: Deserialized message body data.
        :type dct: dict
        :return: TransportPayload instance.
        :rtype: TransportPayload
        """
        if 'expires' in dct:
            expires = dct['expires']
            if dct['expires'] is not None:
                expires = dateutil_parse(dct['expires'])
        else:
            # Backward compatibility for old messages otherwise they are infinite by default.
            expires = get_message_expiration_dt()

        return cls(
            dct['signal_type'],
            dct['cqrs_id'],
            dct['instance_data'],
            dct.get('instance_pk'),
            previous_data=dct.get('previous_data'),
            correlation_id=dct.get('correlation_id'),
            expires=expires,
            retries=dct.get('retries') or 0,
            meta=dct.get('meta'),
        )

    @property
    def signal_type(self):
        return self.__signal_type

    @property
    def cqrs_id(self):
        return self.__cqrs_id

    @property
    def instance_data(self):
        return self.__instance_data

    @property
    def pk(self):
        return self.__instance_pk

    @property
    def queue(self):
        return self.__queue

    @property
    def previous_data(self):
        return self.__previous_data

    @property
    def correlation_id(self):
        return self.__correlation_id

    @property
    def meta(self):
        return self.__meta

    @property
    def expires(self):
        return self.__expires

    @property
    def retries(self):
        return self.__retries

    @retries.setter
    def retries(self, value):
        assert value >= 0, "Payload retries field should be 0 or positive integer."
        self.__retries = value

    def to_dict(self):
        """Return the payload as a dictionary.

        :return: This payload.
        :rtype: dict
        """
        expires = self.__expires
        if expires:
            expires = expires.replace(microsecond=0).isoformat()

        return {
            'signal_type': self.__signal_type,
            'cqrs_id': self.__cqrs_id,
            'instance_data': self.__instance_data,
            'previous_data': self.__previous_data,
            'instance_pk': get_json_valid_value(self.__instance_pk),
            'correlation_id': get_json_valid_value(self.__correlation_id),
            'retries': self.__retries,
            'expires': expires,
            'meta': self.__meta,
        }

    def is_expired(self):
        """Checks if this payload is expired.

        :return: True if payload is expired, False otherwise.
        :rtype: bool
        """
        return (
            self.__expires is not None
            and self.__expires <= timezone.now()
        )
