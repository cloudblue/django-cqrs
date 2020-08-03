#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import logging

from django.conf import settings

logger = logging.getLogger('django-cqrs')


class RegistryMixin:
    @classmethod
    def register_model(cls, model_cls):
        """ Registration of CQRS model identifiers. """
        assert model_cls.CQRS_ID not in cls.models, "Two models can't have the same CQRS_ID: {}." \
            .format(model_cls.CQRS_ID)
        cls.models[model_cls.CQRS_ID] = model_cls

    @classmethod
    def get_model_by_cqrs_id(cls, cqrs_id):
        """
        Returns the model class given its CQRS_ID.

        :param cqrs_id: The CQRS_ID of the model to be retrieved.
        :type cqrs_id: str
        :return: The model that correspond to the given CQRS_ID or None if it
                 has not been registered.
        :rtype: django.db.models.Model
        """
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
            'CQRS queue must be set for the service, that has replica models.'
        super(ReplicaRegistry, cls).register_model(model_cls)
