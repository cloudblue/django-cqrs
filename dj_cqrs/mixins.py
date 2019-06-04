from __future__ import unicode_literals

import logging
from itertools import chain

import six
from django.db import Error, transaction
from django.db.models import DateTimeField, IntegerField, Manager, Model, base, F
from django.utils import timezone

from dj_cqrs.constants import ALL_BASIC_FIELDS
from dj_cqrs.registries import MasterRegistry, ReplicaRegistry
from dj_cqrs.signals import MasterSignals, post_bulk_create, post_update

logger = logging.getLogger()


class _MetaUtils(object):
    @classmethod
    def check_cqrs_field_setting(cls, model_cls, cqrs_field_names, cqrs_attr):
        cls._check_no_duplicate_names(model_cls, cqrs_field_names, cqrs_attr)
        cls._check_id_in_names(model_cls, cqrs_field_names, cqrs_attr)
        cls._check_unexisting_names(model_cls, cqrs_field_names, cqrs_attr)

    @staticmethod
    def check_cqrs_id(model_cls):
        """ Check that CQRS Model has CQRS_ID set up. """
        assert model_cls.CQRS_ID, 'CQRS_ID must be set for every model, that uses CQRS.'

    @staticmethod
    def _check_no_duplicate_names(model_cls, cqrs_field_names, cqrs_attr):
        model_name = model_cls.__name__

        assert len(set(cqrs_field_names)) == len(cqrs_field_names), \
            'Duplicate names in {} field for model {}.'.format(cqrs_attr, model_name)

    @staticmethod
    def _check_unexisting_names(model_cls, cqrs_field_names, cqrs_attr):
        opts = model_cls._meta
        model_name = model_cls.__name__

        model_field_names = {f.name for f in chain(opts.concrete_fields, opts.private_fields)}
        assert not set(cqrs_field_names) - model_field_names, \
            '{} field is not setup correctly for model {}.'.format(cqrs_attr, model_name)

    @staticmethod
    def _check_id_in_names(model_cls, cqrs_field_names, cqrs_attr):
        opts = model_cls._meta
        model_name = model_cls.__name__

        pk_name = opts.pk.name
        assert pk_name in cqrs_field_names, \
            'PK is not in {} for model {}.'.format(cqrs_attr, model_name)


class _MasterMeta(base.ModelBase):
    def __new__(mcs, *args):
        model_cls = super(_MasterMeta, mcs).__new__(mcs, *args)

        if args[0] != 'MasterMixin':
            _MetaUtils.check_cqrs_id(model_cls)
            _MasterMeta._check_cqrs_fields(model_cls)
            MasterRegistry.register_model(model_cls)
            MasterSignals.register_model(model_cls)

        return model_cls

    @staticmethod
    def _check_cqrs_fields(model_cls):
        """ Check that model has correct CQRS fields configuration.

        :param dj_cqrs.mixins.MasterMixin model_cls: CQRS Master Model.
        :raises: AssertionError
        """
        if model_cls.CQRS_FIELDS != ALL_BASIC_FIELDS:
            cqrs_field_names = list(model_cls.CQRS_FIELDS)
            _MetaUtils.check_cqrs_field_setting(model_cls, cqrs_field_names, 'CQRS_FIELDS')


class _MasterManager(Manager):
    def bulk_update(self, queryset, **kwargs):
        """ Custom update method to support sending update signals.

        :param django.db.models.QuerySet queryset: Django Queryset (f.e. filter)
        :param kwargs: Update kwargs
        """
        with transaction.atomic():
            current_dt = timezone.now()
            result = queryset.update(
                cqrs_counter=F('cqrs_counter') + 1, cqrs_updated=current_dt, **kwargs
            )
        queryset.model.call_post_update(list(queryset.all()))
        return result


class MasterMixin(six.with_metaclass(_MasterMeta, Model)):
    """
    Mixin for the master CQRS model, that will send data updates to it's replicas.

    CQRS_FIELDS - Fields, that need to by synchronized between microservices.
    CQRS_ID - Unique CQRS identifier for all microservices.
    cqrs - Manager, that adds needed CQRS queryset methods.
    """
    CQRS_FIELDS = ALL_BASIC_FIELDS
    CQRS_ID = None

    objects = Manager()
    cqrs = _MasterManager()

    cqrs_counter = IntegerField(
        default=0, help_text="This field must be incremented on any model update. "
                             "It's used to for CQRS sync.",
    )
    cqrs_updated = DateTimeField(
        auto_now=True, help_text="This field must be incremented on every model update. "
                                 "It's used to for CQRS sync.",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            self.cqrs_counter = F('cqrs_counter') + 1
        return super(MasterMixin, self).save(*args, **kwargs)

    def model_to_cqrs_dict(self):
        """ CQRS serialization for transport payload. """
        opts = self._meta

        if isinstance(self.CQRS_FIELDS, six.string_types) and self.CQRS_FIELDS == ALL_BASIC_FIELDS:
            included_fields = None
        else:
            included_fields = self.CQRS_FIELDS

        data = {}
        for f in chain(opts.concrete_fields, opts.private_fields):
            if included_fields and (f.name not in included_fields):
                continue

            data[f.name] = f.value_from_object(self)

        # We need to include additional fields for synchronisation, f.e. to prevent de-duplication
        for cqrs_tech_field_name in ('cqrs_counter', 'cqrs_updated'):
            data[cqrs_tech_field_name] = getattr(self, cqrs_tech_field_name)

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
            # Used automatically by cqrs.bulk_update()
            qs = model.objects.filter(k1=v1)
            model.cqrs.bulk_update(qs, k2=v2)
        """
        post_update.send(cls, instances=instances)


class _ReplicaMeta(base.ModelBase):
    def __new__(mcs, *args):
        model_cls = super(_ReplicaMeta, mcs).__new__(mcs, *args)

        if args[0] != 'ReplicaMixin':
            _MetaUtils.check_cqrs_id(model_cls)
            _ReplicaMeta._check_cqrs_mapping(model_cls)
            ReplicaRegistry.register_model(model_cls)

        return model_cls

    @staticmethod
    def _check_cqrs_mapping(model_cls):
        """ Check that model has correct CQRS mapping configuration.

        :param dj_cqrs.mixins.ReplicaMixin model_cls: CQRS Replica Model.
        :raises: AssertionError
        """
        if model_cls.CQRS_MAPPING is not None:
            cqrs_field_names = list(model_cls.CQRS_MAPPING.values())
            _MetaUtils.check_cqrs_field_setting(model_cls, cqrs_field_names, 'CQRS_MAPPING')


class ReplicaMixin(six.with_metaclass(_ReplicaMeta, Model)):
    """
    Mixin for the replica CQRS model, that will receive data updates from master. Models, using
    this mixin should be readonly, but this is not enforced (f.e. for admin).

    CQRS_ID - Unique CQRS identifier for all microservices.
    CQRS_MAPPING - Mapping of master data field name to replica model field name.

    Django docs state, that for model level functions we need to use model managers. The problem is
    that some models need to override behaviour of model level functions. Manager level
    implementation would bring unneeded level of complexity for support and increase model-manager
    coupling.
    """
    CQRS_ID = None
    CQRS_MAPPING = None

    cqrs_counter = IntegerField()
    cqrs_updated = DateTimeField()

    class Meta:
        abstract = True

    @classmethod
    def cqrs_save(cls, master_data):
        mapped_data = cls._map_save_data(master_data)
        if mapped_data:
            raise NotImplementedError

    @classmethod
    def cqrs_delete(cls, master_data):
        mapped_data = cls._map_delete_data(master_data)
        if mapped_data:
            try:
                pk_name = cls._get_pk_name()
                pk_value = mapped_data[pk_name]
                cls._default_manager.filter(**{pk_name: pk_value}).delete()
            except Error as e:
                logger.error('{}\npk = {}'.format(str(e), pk_value))

    @classmethod
    def _get_pk_name(cls):
        return cls._meta.pk.name

    @classmethod
    def _map_save_data(cls, master_data):
        if cls.CQRS_MAPPING is not None:
            mapped_data = {}
            for master_name, replica_name in cls.CQRS_MAPPING.items():
                if master_name not in master_data:
                    logger.error('Bad master-replica mapping for {} ({}).'.format(
                        master_name, cls.CQRS_ID,
                    ))
                    return

                mapped_data[replica_name] = master_data[master_name]

        else:
            mapped_data = master_data

        if cls._get_pk_name() not in mapped_data:
            cls._log_pk_data_error()
            return

        if cls._cqrs_fields_are_filled(mapped_data):
            return mapped_data

    @classmethod
    def _map_delete_data(cls, master_data):
        if 'id' not in master_data:
            cls._log_pk_data_error()
            return

        if not cls._cqrs_fields_are_filled(master_data):
            return

        return {
            cls._get_pk_name(): master_data['id'],
            'cqrs_counter': master_data['cqrs_counter'],
            'cqrs_updated': master_data['cqrs_updated'],
        }

    @classmethod
    def _cqrs_fields_are_filled(cls, data):
        if 'cqrs_counter' in data and 'cqrs_updated' in data:
            return True

        logger.error('CQRS sync fields are not provided in data ({}).'.format(cls.CQRS_ID))
        return False

    @classmethod
    def _log_pk_data_error(cls):
        logger.error('PK is not provided in data ({}).'.format(cls.CQRS_ID))
