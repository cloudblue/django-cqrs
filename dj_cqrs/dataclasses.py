#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from dj_cqrs.correlation import get_correlation_id


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
    ):
        self.__signal_type = signal_type
        self.__cqrs_id = cqrs_id
        self.__instance_data = instance_data
        self.__instance_pk = instance_pk
        self.__queue = queue
        self.__previous_data = previous_data

        if correlation_id:
            self.__correlation_id = correlation_id
        else:
            self.__correlation_id = get_correlation_id(signal_type, cqrs_id, instance_pk, queue)

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

    def to_dict(self):
        """
        Return the payload as a dictionary.

        :return: This payload.
        :rtype: dict
        """
        return {
            'signal_type': self.__signal_type,
            'cqrs_id': self.__cqrs_id,
            'instance_data': self.__instance_data,
            'previous_data': self.__previous_data,
            'instance_pk': self.__instance_pk,
            'correlation_id': self.__correlation_id,
        }
