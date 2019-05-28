from __future__ import unicode_literals

from itertools import chain

import six
from django.db.models import Model, base

from .signals import MasterSignals


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


class MasterMixin(six.with_metaclass(_MasterMeta, Model)):
    CQRS_FIELDS = '__all__'
    CQRS_ID = None

    class Meta:
        abstract = True

    def model_to_cqrs_dict(self):
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
