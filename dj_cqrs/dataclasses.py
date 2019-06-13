from __future__ import unicode_literals


class TransportPayload(object):
    def __init__(self, signal_type, cqrs_id, instance_data, instance_pk=None, queue=None):
        self.__signal_type = signal_type
        self.__cqrs_id = cqrs_id
        self.__instance_data = instance_data
        self.__instance_pk = instance_pk
        self.__queue = queue

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

    def to_dict(self):
        return {
            'signal_type': self.__signal_type,
            'cqrs_id': self.__cqrs_id,
            'instance_data': self.__instance_data,
        }
