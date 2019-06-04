from __future__ import unicode_literals

import logging

from django.conf import settings

logger = logging.getLogger()


class RegistryMixin(object):
    @classmethod
    def register_model(cls, model_cls):
        """ Registration of CQRS model identifiers. """
        assert model_cls.CQRS_ID not in cls.models, "Two models can't have the same CQRS_ID: {}." \
            .format(model_cls.CQRS_ID)
        cls.models[model_cls.CQRS_ID] = model_cls

    @classmethod
    def get_model_by_cqrs_id(cls, cqrs_id):
        if cqrs_id in cls.models:
            return cls.models[cqrs_id]

        logger.error('No model with such CQRS_ID: {}.'.format(cqrs_id))


class MasterRegistry(RegistryMixin):
    models = {}


class ReplicaRegistry(RegistryMixin):
    models = {}

    @classmethod
    def register_model(cls, model_cls):
        assert getattr(settings, 'CQRS', {}).get('queue') is not None, \
            'CQRS queue must be setup for the service, that has replica models.'
        super(ReplicaRegistry, cls).register_model(model_cls)
