from __future__ import unicode_literals


class BaseTransport(object):
    @staticmethod
    def publish(payload):
        raise NotImplementedError

    @staticmethod
    def consume(payload):
        raise NotImplementedError
