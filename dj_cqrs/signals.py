from __future__ import unicode_literals

from django.db import models
from dj_cqrs.transport import current_transport


class MasterSignals(object):
    @classmethod
    def register_model(cls, model_cls):
        models.signals.post_save.connect(cls.post_save, sender=model_cls)
        models.signals.post_delete.connect(cls.post_delete, sender=model_cls)

    @classmethod
    def post_save(cls, sender, **kwargs):
        instance_data = kwargs['instance'].model_to_cqrs_dict()
        signal = 'post_save'

        payload = {'signal': signal, 'instance': instance_data, 'cqrs_id': sender.CQRS_ID}
        current_transport.publish(payload)

    @classmethod
    def post_delete(cls, sender, **kwargs):
        instance_data = {'id': kwargs['instance'].pk}
        signal = 'post_delete'

        payload = {'signal': signal, 'instance': instance_data, 'cqrs_id': sender.CQRS_ID}
        current_transport.publish(payload)
