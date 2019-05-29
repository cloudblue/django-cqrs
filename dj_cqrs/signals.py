from __future__ import unicode_literals

from django.db import models
from django.dispatch import Signal

from dj_cqrs.transport import current_transport


class SignalType(object):
    DELETE = 'DELETE'
    SAVE = 'SAVE'


post_bulk_create = Signal(providing_args=['instances'])
post_update = Signal(providing_args=['instances'])


class MasterSignals(object):
    """ Signals registry and handlers for CQRS master models. """
    @classmethod
    def register_model(cls, model_cls):
        """
        :param dj_cqrs.mixins.MasterMixin model_cls: Class inherited from CQRS MasterMixin.
        """
        models.signals.post_save.connect(cls.post_save, sender=model_cls)
        models.signals.post_delete.connect(cls.post_delete, sender=model_cls)

        post_bulk_create.connect(cls.post_bulk_create, sender=model_cls)
        post_update.connect(cls.post_update, sender=model_cls)

    @classmethod
    def post_save(cls, sender, **kwargs):
        """
        :param dj_cqrs.mixins.MasterMixin sender: Class or instance inherited from CQRS MasterMixin.
        """
        instance_data = kwargs['instance'].model_to_cqrs_dict()
        signal = SignalType.SAVE

        payload = {'signal': signal, 'instance': instance_data, 'cqrs_id': sender.CQRS_ID}
        current_transport.produce(payload)

    @classmethod
    def post_delete(cls, sender, **kwargs):
        """
        :param dj_cqrs.mixins.MasterMixin sender: Class or instance inherited from CQRS MasterMixin.
        """
        instance_data = {'id': kwargs['instance'].pk}
        signal = SignalType.DELETE

        payload = {'signal': signal, 'instance': instance_data, 'cqrs_id': sender.CQRS_ID}
        current_transport.produce(payload)

    @classmethod
    def post_bulk_create(cls, sender, **kwargs):
        """
        :param dj_cqrs.mixins.MasterMixin sender: Class or instance inherited from CQRS MasterMixin.
        """
        for instance in kwargs['instances']:
            cls.post_save(sender, instance=instance)

    @classmethod
    def post_update(cls, sender, **kwargs):
        """
        :param dj_cqrs.mixins.MasterMixin sender: Class or instance inherited from CQRS MasterMixin.
        """
        for instance in kwargs['instances']:
            cls.post_save(sender, instance=instance)
