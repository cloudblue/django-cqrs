from __future__ import unicode_literals


class ReplicaFactory(object):
    models = {}

    @classmethod
    def register_model(cls, model_cls):
        """ Registration of CQRS model identifiers for consuming.

        :param dj_cqrs.mixins.ReplicaMixin model_cls: Class inherited from CQRS ReplicaMixin.
        """
        cls.models[model_cls.CQRS_ID] = model_cls

    @staticmethod
    def factory(signal_type, cqrs_id, instance_data):
        """ Factory method to update replica instance.

        :param dj_cqrs.constants.SignalType signal_type: Consumed signal type.
        :param str cqrs_id: Replica model CQRS unique identifier.
        :param dict instance_data: Master model data.
        :return:
        """
        pass
