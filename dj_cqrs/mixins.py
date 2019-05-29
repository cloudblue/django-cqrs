from __future__ import unicode_literals

from itertools import chain

import six
from django.db.models import Manager, Model, base

from .signals import MasterSignals, post_bulk_create, post_update


class _MasterMeta(base.ModelBase):
    def __new__(mcs, *args):
        model_cls = super(_MasterMeta, mcs).__new__(mcs, *args)
        _MasterMeta.check_cqrs_id(model_cls, args[0])

        MasterSignals.register_model(model_cls)
        return model_cls

    @staticmethod
    def check_cqrs_id(model_cls, model_name):
        if model_name != 'MasterMixin':
            assert model_cls.CQRS_ID, 'CQRS_ID must be set for every model, that uses CQRS.'


class _MasterManager(Manager):
    def update(self, queryset, *args, **kwargs):
        """ Custom update method to support sending update signals.

        :param queryset: Django Queryset (f.e. filter)
        :param args: Update args
        :param kwargs: Update kwargs
        """
        queryset.update(*args, **kwargs)
        queryset.model.call_post_update(list(queryset.all()))


class MasterMixin(six.with_metaclass(_MasterMeta, Model)):
    """
    Mixin for the master CQRS model, that will send data updates to it's replicas.

    CQRS_FIELDS - Fields, that need to by synchronized between microservices.
    CQRS_ID - Unique CQRS identifier for all microservices.
    cqrs - Manager, that adds needed CQRS queryset methods.
    """
    CQRS_FIELDS = '__all__'
    CQRS_ID = None

    objects = Manager()
    cqrs = _MasterManager()

    class Meta:
        abstract = True

    def model_to_cqrs_dict(self):
        """ CQRS serialization for transport payload. """
        opts = self._meta

        if isinstance(self.CQRS_FIELDS, six.string_types) and self.CQRS_FIELDS == '__all__':
            exclude_set = None
        else:
            exclude_set = self.CQRS_FIELDS

        data = {}
        for f in chain(opts.concrete_fields, opts.private_fields):
            if exclude_set and (f.name not in exclude_set):
                continue

            data[f.name] = f.value_from_object(self)
        return data

    def cqrs_sync(self):
        """ Manual instance synchronization. """
        if self._state.adding:
            return False
        try:
            self.refresh_from_db()
        except self._meta.model.DoesNotExist:
            return False

        MasterSignals.post_save(self._meta.model, instance=self)
        return True

    @classmethod
    def call_post_bulk_create(cls, instances):
        """ Post bulk create signal caller (django doesn't support it by default).

        .. code-block:: python
            # On PostgreSQL
            instances = model.objects.bulk_create(instances)
            model.call_post_bulk_create(instances)
        """
        post_bulk_create.send(cls, instances=instances)

    @classmethod
    def call_post_update(cls, instances):
        """ Post bulk update signal caller (django doesn't support it by default).

        .. code-block:: python
            # Used automatically by cqrs.update()
            qs = model.objects.filter(k1=v1)
            model.cqrs.update(qs, k2=v2)
        """
        post_update.send(cls, instances=instances)
