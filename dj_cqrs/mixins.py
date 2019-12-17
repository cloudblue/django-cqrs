from itertools import chain

import six
from django.db.models import DateField, DateTimeField, F, IntegerField, Manager, Model
from django.db.models.expressions import CombinedExpression
from django.utils.module_loading import import_string

from dj_cqrs.constants import ALL_BASIC_FIELDS
from dj_cqrs.managers import MasterManager, ReplicaManager
from dj_cqrs.metas import MasterMeta, ReplicaMeta
from dj_cqrs.signals import MasterSignals, post_bulk_create, post_update


class MasterMixin(six.with_metaclass(MasterMeta, Model)):
    """
    Mixin for the master CQRS model, that will send data updates to it's replicas.

    CQRS_ID - Unique CQRS identifier for all microservices.
    CQRS_FIELDS - Fields, that need to by synchronized between microservices.
    CQRS_SERIALIZER - Serializer, that overrides common serialization logic.
                      Can't be set together with non-default CQRS_FIELDS.
                      DRF serializers are only supported now: Serializer(instance).data

    cqrs - Manager, that adds needed CQRS queryset methods.
    """
    CQRS_ID = None

    CQRS_FIELDS = ALL_BASIC_FIELDS
    CQRS_SERIALIZER = None  # It must be None or string, like: 'path.to.serializer'

    objects = Manager()
    cqrs = MasterManager()

    cqrs_revision = IntegerField(
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
            self.cqrs_revision = F('cqrs_revision') + 1
        return super(MasterMixin, self).save(*args, **kwargs)

    def to_cqrs_dict(self, using=None):
        """ CQRS serialization for transport payload. """
        if self.CQRS_SERIALIZER:
            data = self._class_serialization(using)
        else:
            data = self._common_serialization(using)
        return data

    def cqrs_sync(self, using=None, queue=None):
        """ Manual instance synchronization. """
        if self._state.adding:
            return False

        if not self.CQRS_SERIALIZER:
            try:
                self.refresh_from_db()
            except self._meta.model.DoesNotExist:
                return False

        MasterSignals.post_save(
            self._meta.model, instance=self, using=using, queue=queue, sync=True,
        )
        return True

    def is_sync_instance(self):
        """
        This method can be overridden to apply syncing only to instances by some rules.
        For example, only objects with special status or after some creation date, etc.

        :return: True if this instance needs to be synced, False otherwise
        :rtype: bool
        """
        return True

    @classmethod
    def relate_cqrs_serialization(cls, queryset):
        """
        :param django.db.models.QuerySet queryset:
        """
        return queryset

    @classmethod
    def call_post_bulk_create(cls, instances, using=None):
        """ Post bulk create signal caller (django doesn't support it by default).

        .. code-block:: python
            # On PostgreSQL
            instances = model.objects.bulk_create(instances)
            model.call_post_bulk_create(instances)
        """
        post_bulk_create.send(cls, instances=instances, using=using)

    @classmethod
    def call_post_update(cls, instances, using=None):
        """ Post bulk update signal caller (django doesn't support it by default).

        .. code-block:: python
            # Used automatically by cqrs.bulk_update()
            qs = model.objects.filter(k1=v1)
            model.cqrs.bulk_update(qs, k2=v2)
        """
        post_update.send(cls, instances=instances, using=using)

    def _common_serialization(self, using):
        if isinstance(self.cqrs_revision, CombinedExpression):
            self.refresh_from_db(fields=('cqrs_revision',), using=using)

        opts = self._meta

        if isinstance(self.CQRS_FIELDS, six.string_types) and self.CQRS_FIELDS == ALL_BASIC_FIELDS:
            included_fields = None
        else:
            included_fields = self.CQRS_FIELDS

        data = {}
        for f in chain(opts.concrete_fields, opts.private_fields):
            if included_fields and (f.name not in included_fields):
                continue

            value = f.value_from_object(self)
            if value is not None and isinstance(f, (DateField, DateTimeField)):
                value = str(value)

            data[f.name] = value

        # We need to include additional fields for synchronisation, f.e. to prevent de-duplication
        data['cqrs_revision'] = self.cqrs_revision
        data['cqrs_updated'] = str(self.cqrs_updated)

        return data

    def _class_serialization(self, using):
        db = using if using is not None else self._state.db
        qs = self.__class__._default_manager.using(db).filter(pk=self.pk)

        instance = self.relate_cqrs_serialization(qs).first()
        if not instance:
            raise RuntimeError("Couldn't serialize CQRS class ({}).".format(self.CQRS_ID))

        data = self._cqrs_serializer_cls(instance).data
        data['cqrs_revision'] = instance.cqrs_revision
        data['cqrs_updated'] = str(instance.cqrs_updated)

        return data

    @property
    def _cqrs_serializer_cls(self):
        """ Serialization class loader. """
        if hasattr(self.__class__, '_cqrs_serializer_class'):
            return self.__class__._cqrs_serializer_class

        try:
            serializer = import_string(self.CQRS_SERIALIZER)
            self.__class__._cqrs_serializer_class = serializer
            return serializer
        except ImportError:
            raise ImportError("Model {}: CQRS_SERIALIZER can't be imported.".format(self.__class__))


class ReplicaMixin(six.with_metaclass(ReplicaMeta, Model)):
    """
    Mixin for the replica CQRS model, that will receive data updates from master. Models, using
    this mixin should be readonly, but this is not enforced (f.e. for admin).

    CQRS_ID - Unique CQRS identifier for all microservices.
    CQRS_MAPPING - Mapping of master data field name to replica model field name.
    CQRS_CUSTOM_SERIALIZATION - To override default data check.
    """
    CQRS_ID = None
    CQRS_MAPPING = None
    CQRS_CUSTOM_SERIALIZATION = False

    objects = Manager()
    cqrs = ReplicaManager()

    cqrs_revision = IntegerField()
    cqrs_updated = DateTimeField()

    class Meta:
        abstract = True

    @classmethod
    def cqrs_save(cls, master_data, sync=False):
        """ This method saves (creates or updates) model instance from CQRS master instance data.
        This method must not be overridden. Otherwise, sync checks need to be implemented manually.

        :param dict master_data: CQRS master instance data.
        :param bool sync: Sync package flag.
        :return: Model instance.
        :rtype: django.db.models.Model
        """
        return cls.cqrs.save_instance(master_data, sync)

    @classmethod
    def cqrs_create(cls, sync, **mapped_data):
        """ This method creates model instance from CQRS mapped instance data. It must be overridden
        by replicas of master models with custom serialization.

        :param dict mapped_data: CQRS mapped instance data.
        :param bool sync: Sync package flag.
        :return: Model instance.
        :rtype: django.db.models.Model
        """
        return cls._default_manager.create(**mapped_data)

    def cqrs_update(self, sync, **mapped_data):
        """ This method updates model instance from CQRS mapped instance data. It must be overridden
        by replicas of master models with custom serialization.

        :param dict mapped_data: CQRS mapped instance data.
        :param bool sync: Sync package flag.
        :return: Model instance.
        :rtype: django.db.models.Model
        """

        for key, value in mapped_data.items():
            setattr(self, key, value)
        self.save()
        return self

    @classmethod
    def cqrs_delete(cls, master_data):
        """ This method deletes model instance from mapped CQRS master instance data.

        :param dict master_data: CQRS master instance data.
        :return: Flag, if delete operation is successful (even if nothing was deleted).
        :rtype: bool
        """
        return cls.cqrs.delete_instance(master_data)
