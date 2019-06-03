from __future__ import unicode_literals


class ReplicaFactory(object):

    @staticmethod
    def factory(signal_type, cqrs_id, instance_data):
        """ Factory method to update replica instance.

        :param dj_cqrs.constants.SignalType signal_type: Consumed signal type.
        :param str cqrs_id: Replica model CQRS unique identifier.
        :param dict instance_data: Master model data.
        :return:
        """
        pass
