from __future__ import unicode_literals


class RegistryMixin(object):
    @classmethod
    def register_model(cls, model_cls):
        """ Registration of CQRS model identifiers. """
        assert model_cls.CQRS_ID not in cls.models, "Two models can't have the same CQRS_ID: {}." \
            .format(model_cls.CQRS_ID)
        cls.models[model_cls.CQRS_ID] = model_cls


class MasterRegistry(RegistryMixin):
    models = {}


class ReplicaRegistry(RegistryMixin):
    models = {}
