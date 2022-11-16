#  Copyright © 2022 Ingram Micro Inc. All rights reserved.

import logging

from dj_cqrs.constants import SignalType
from dj_cqrs.controller import producer
from dj_cqrs.dataclasses import TransportPayload
from dj_cqrs.utils import get_message_expiration_dt

from django.db import models, transaction
from django.dispatch import Signal
from django.utils.timezone import now


logger = logging.getLogger('django-cqrs')

post_bulk_create = Signal()
"""
Signal sent after a bulk create.
See dj_cqrs.mixins.RawMasterMixin.call_post_bulk_create.
"""

post_update = Signal()
"""
Signal sent after a bulk update.
See dj_cqrs.mixins.RawMasterMixin.call_post_update.
"""


class MasterSignals:
    """ Signals registry and handlers for CQRS master models. """
    @classmethod
    def register_model(cls, model_cls):
        """
        Registers signals for a model.

        :param model_cls:  Model class inherited from CQRS MasterMixin.
        :type model_cls: dj_cqrs.mixins.MasterMixin
        """

        models.signals.post_save.connect(cls.post_save, sender=model_cls)
        models.signals.post_delete.connect(cls.post_delete, sender=model_cls)

        post_bulk_create.connect(cls.post_bulk_create, sender=model_cls)
        post_update.connect(cls.post_bulk_update, sender=model_cls)

    @classmethod
    def post_save(cls, sender, **kwargs):
        """
        :param dj_cqrs.mixins.MasterMixin sender: Class or instance inherited from CQRS MasterMixin.
        """
        if not sender.CQRS_PRODUCE:
            return

        update_fields = kwargs.get('update_fields')
        if update_fields and ('cqrs_revision' not in update_fields):
            return

        instance = kwargs['instance']
        if not instance.is_sync_instance():
            return

        using = kwargs['using']

        sync = kwargs.get('sync', False)
        queue = kwargs.get('queue', None)

        connection = transaction.get_connection(using)
        if not connection.in_atomic_block or instance.is_initial_cqrs_save:
            transaction.on_commit(
                lambda: cls._post_save_produce(sender, instance, using, sync, queue),
            )

    @classmethod
    def _post_save_produce(cls, sender, instance, using, sync, queue):
        # As this method may run 'on_commit', the instance may not exist. In that case, log the
        # error but don't raise an exception.
        try:
            instance.reset_cqrs_saves_count()
            instance_data = instance.to_cqrs_dict(using, sync=sync)
            previous_data = instance.get_tracked_fields_data()
            signal_type = SignalType.SYNC if sync else SignalType.SAVE
            meta = instance.get_cqrs_meta(
                instance_data=instance_data,
                previous_data=previous_data,
                signal_type=signal_type,
            )
        except sender.DoesNotExist:
            logger.error(
                f"Can't produce message from master model '{sender.__name__}': "
                f"The instance doesn't exist (pk={instance.pk})",
            )
            return

        payload = TransportPayload(
            signal_type,
            sender.CQRS_ID,
            instance_data,
            instance.pk,
            queue,
            previous_data,
            expires=get_message_expiration_dt(),
            meta=meta,
        )
        producer.produce(payload)

    @classmethod
    def post_delete(cls, sender, **kwargs):
        """
        :param dj_cqrs.mixins.MasterMixin sender: Class or instance inherited from CQRS MasterMixin.
        """
        if not sender.CQRS_PRODUCE:
            return

        instance = kwargs['instance']
        if not instance.is_sync_instance():
            return

        instance_data = {
            'id': instance.pk,
            'cqrs_revision': instance.cqrs_revision + 1,
            'cqrs_updated': str(now()),
        }

        data = instance.get_custom_cqrs_delete_data()
        if data:
            instance_data['custom'] = data

        signal_type = SignalType.DELETE

        meta = instance.get_cqrs_meta(
            instance_data=instance_data,
            signal_type=signal_type,
        )

        payload = TransportPayload(
            signal_type,
            sender.CQRS_ID,
            instance_data,
            instance.pk,
            expires=get_message_expiration_dt(),
            meta=meta,
        )
        # Delete is always in transaction!
        transaction.on_commit(lambda: producer.produce(payload))

    @classmethod
    def post_bulk_create(cls, sender, **kwargs):
        """
        :param dj_cqrs.mixins.MasterMixin sender: Class or instance inherited from CQRS MasterMixin.
        """
        cls._post_bulk(sender, **kwargs)

    @classmethod
    def post_bulk_update(cls, sender, **kwargs):
        """
        :param dj_cqrs.mixins.MasterMixin sender: Class or instance inherited from CQRS MasterMixin.
        """
        cls._post_bulk(sender, **kwargs)

    @classmethod
    def _post_bulk(cls, sender, **kwargs):
        for instance in kwargs['instances']:
            cls.post_save(sender, instance=instance, using=kwargs['using'])
