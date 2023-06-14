#  Copyright © 2023 Ingram Micro Inc. All rights reserved.

import logging

from django.conf import settings
from django.db import router, transaction
from django.db.models import (
    DateField,
    DateTimeField,
    F,
    IntegerField,
    Manager,
    Model,
    UUIDField,
)
from django.db.models.expressions import CombinedExpression
from django.utils.module_loading import import_string

from dj_cqrs.constants import ALL_BASIC_FIELDS, FIELDS_TRACKER_FIELD_NAME, TRACKED_FIELDS_ATTR_NAME
from dj_cqrs.managers import MasterManager, ReplicaManager
from dj_cqrs.metas import MasterMeta, ReplicaMeta
from dj_cqrs.signals import MasterSignals, post_bulk_create, post_update


logger = logging.getLogger('django-cqrs')


class RawMasterMixin(Model):

    """Base class for MasterMixin. **Users shouldn't use this
    class directly.**"""

    CQRS_ID = None
    """Unique CQRS identifier for all microservices."""

    CQRS_PRODUCE = True
    """If false, no cqrs data is sent through the transport."""

    CQRS_FIELDS = ALL_BASIC_FIELDS
    """
    List of fields to include in the CQRS payload.
    You can also set the fields attribute to the special value '__all__'
    to indicate that all fields in the model should be used.
    """

    CQRS_SERIALIZER = None
    """
    Optional serializer used to create the instance representation.
    Must be expressed as a module dotted path string like
    `mymodule.serializers.MasterModelSerializer`.
    """

    CQRS_TRACKED_FIELDS = None
    """
    List of fields of the main model for which you want to track the changes
    and send the previous values via transport. You can also set the field
    attribute to the special value "__all__" to indicate that all fields in
    the model must be used.
    """

    objects = Manager()

    cqrs = MasterManager()
    """Manager that adds needed CQRS queryset methods."""

    cqrs_revision = IntegerField(
        default=0,
        help_text='This field must be incremented on any model update. '
        "It's used to for CQRS sync.",
    )
    cqrs_updated = DateTimeField(
        auto_now=True,
        help_text='This field must be incremented on every model update. '
        "It's used to for CQRS sync.",
    )

    class Meta:
        abstract = True

    @property
    def cqrs_saves_count(self):
        """Shows how many times this instance has been saved within the transaction."""
        return getattr(self, '_cqrs_saves_count', 0)

    @property
    def is_initial_cqrs_save(self):
        """This flag is used to check if instance has already been registered for CQRS update."""
        return self.cqrs_saves_count < 2

    def reset_cqrs_saves_count(self):
        """This method is used to automatically reset instance CQRS counters on transaction commit.
        But this can also be used to control custom behaviour within transaction
        or in case of rollback,
        when several sequential transactions are used to change the same instance.
        """
        if hasattr(self, '_cqrs_saves_count'):
            self._cqrs_saves_count = 0

    def save(self, *args, **kwargs):
        update_fields = kwargs.pop('update_fields', None)
        update_cqrs_fields = kwargs.pop('update_cqrs_fields', self._update_cqrs_fields_default)

        using = kwargs.get('using') or router.db_for_write(self.__class__, instance=self)
        connection = transaction.get_connection(using)
        if connection.in_atomic_block:
            _cqrs_saves_count = self.cqrs_saves_count
            self._cqrs_saves_count = _cqrs_saves_count + 1
        else:
            self.reset_cqrs_saves_count()

        if (not update_fields) and self.is_initial_cqrs_save and (not self._state.adding):
            self.cqrs_revision = F('cqrs_revision') + 1
        elif update_fields and update_cqrs_fields:
            self.cqrs_revision = F('cqrs_revision') + 1
            update_fields = set(update_fields)
            update_fields.update({'cqrs_revision', 'cqrs_updated'})

        kwargs['update_fields'] = update_fields

        self.save_tracked_fields()

        return super(RawMasterMixin, self).save(*args, **kwargs)

    def save_tracked_fields(self):
        if hasattr(self, FIELDS_TRACKER_FIELD_NAME):
            tracker = getattr(self, FIELDS_TRACKER_FIELD_NAME)
            if self.is_initial_cqrs_save:
                if self._state.adding:
                    data = tracker.changed_initial()
                else:
                    data = tracker.changed()
                setattr(self, TRACKED_FIELDS_ATTR_NAME, data)

    @property
    def _update_cqrs_fields_default(self):
        return settings.CQRS['master']['CQRS_AUTO_UPDATE_FIELDS']

    def to_cqrs_dict(self, using: str = None, sync: bool = False) -> dict:
        """CQRS serialization for transport payload.

        Args:
            using (str): The using argument can be used to force the database to use,
                defaults to None.
            sync (bool): optional

        Returns:
            (dict): The serialized instance data.
        """
        if self.CQRS_SERIALIZER:
            data = self._class_serialization(using, sync=sync)
        else:
            self._refresh_f_expr_values(using)
            data = self._common_serialization(using)
        return data

    def get_tracked_fields_data(self) -> dict:
        """CQRS serialization for tracked fields to include
        in the transport payload.

        Returns:
            (dict): Previous values for tracked fields.
        """
        return getattr(self, TRACKED_FIELDS_ATTR_NAME, None)

    def cqrs_sync(self, using: str = None, queue: str = None) -> bool:
        """Manual instance synchronization.

        Args:
            using (str): The using argument can be used to force the database
                to use, defaults to None.
            queue (str): Syncing can be executed just for a single queue, defaults to None
                 (all queues).

        Returns:
            (bool): True if instance can be synced, False otherwise.
        """
        if self._state.adding:
            return False

        if not self.CQRS_SERIALIZER:
            try:
                self.refresh_from_db()
            except self._meta.model.DoesNotExist:
                return False

        MasterSignals.post_save(
            self._meta.model,
            instance=self,
            using=using,
            queue=queue,
            sync=True,
        )
        return True

    def is_sync_instance(self) -> bool:
        """
        This method can be overridden to apply syncing only to instances by some rules.
        For example, only objects with special status or after some creation date, etc.

        Returns:
            (bool): True if this instance needs to be synced, False otherwise.
        """
        return True

    def get_cqrs_meta(self, **kwargs: dict) -> dict:
        """
        This method can be overridden to collect model/instance specific metadata.

        Args:
            kwargs (dict): Signal type, payload data, etc.

        Returns:
            (dict): Metadata dictionary if it's provided.
        """
        generic_meta_func = settings.CQRS['master']['meta_function']
        if generic_meta_func:
            return generic_meta_func(obj=self, **kwargs)

        return {}

    @classmethod
    def relate_cqrs_serialization(cls, queryset):
        """
        This method shoud be overriden to optimize database access
        for example using `select_related` and `prefetch_related`
        when related models must be included into the master model
        representation.

        Args:
            queryset (django.db.models.QuerySet): The initial queryset.

        Returns:
            (django.db.models.QuerySet): The optimized queryset.

        """
        return queryset

    def get_custom_cqrs_delete_data(self):
        """This method should be overridden when additional data is needed in DELETE payload."""
        pass

    @classmethod
    def call_post_bulk_create(cls, instances: list, using=None):
        """Post bulk create signal caller (django doesn't support it by default).

        ``` py3

            # Used automatically by cqrs.bulk_create()
            instances = model.cqrs.bulk_create(instances)
        ```
        """
        post_bulk_create.send(cls, instances=instances, using=using)

    @classmethod
    def call_post_update(cls, instances, using=None):
        """Post bulk update signal caller (django doesn't support it by default).

        ``` py3

            # Used automatically by cqrs.bulk_update()
            qs = model.objects.filter(k1=v1)
            model.cqrs.bulk_update(qs, k2=v2)
        ```
        """
        post_update.send(cls, instances=instances, using=using)

    def _common_serialization(self, using):
        opts = self._meta

        if isinstance(self.CQRS_FIELDS, str) and self.CQRS_FIELDS == ALL_BASIC_FIELDS:
            included_fields = None
        else:
            included_fields = self.CQRS_FIELDS

        data = {}
        for f in opts.fields:
            if included_fields and (f.name not in included_fields):
                continue

            value = f.value_from_object(self)
            if value is not None and isinstance(f, (DateField, DateTimeField, UUIDField)):
                value = str(value)

            data[f.name] = value

        # We need to include additional fields for synchronisation, f.e. to prevent de-duplication
        data['cqrs_revision'] = self.cqrs_revision
        data['cqrs_updated'] = str(self.cqrs_updated)

        return data

    def _class_serialization(self, using, sync=False):
        if sync:
            instance = self
        else:
            db = using if using is not None else self._state.db
            qs = self.__class__._default_manager.using(db)
            instance = self.relate_cqrs_serialization(qs).get(pk=self.pk)

        data = self._cqrs_serializer_cls(instance).data
        data['cqrs_revision'] = instance.cqrs_revision
        data['cqrs_updated'] = str(instance.cqrs_updated)

        return data

    def _refresh_f_expr_values(self, using):
        opts = self._meta
        fields_to_refresh = []
        if isinstance(self.cqrs_revision, CombinedExpression):
            fields_to_refresh.append('cqrs_revision')

        if isinstance(self.CQRS_FIELDS, str) and self.CQRS_FIELDS == ALL_BASIC_FIELDS:
            included_fields = None
        else:
            included_fields = self.CQRS_FIELDS

        for f in opts.fields:
            if included_fields and (f.name not in included_fields):
                continue

            value = f.value_from_object(self)

            if value is not None and isinstance(value, CombinedExpression):
                fields_to_refresh.append(f.name)

        if fields_to_refresh:
            self.refresh_from_db(fields=fields_to_refresh)

    @property
    def _cqrs_serializer_cls(self):
        """Serialization class loader."""
        if hasattr(self.__class__, '_cqrs_serializer_class'):
            return self.__class__._cqrs_serializer_class

        try:
            serializer = import_string(self.CQRS_SERIALIZER)
            self.__class__._cqrs_serializer_class = serializer
            return serializer
        except ImportError:
            raise ImportError(
                "Model {0}: CQRS_SERIALIZER can't be imported.".format(self.__class__),
            )


class MasterMixin(RawMasterMixin, metaclass=MasterMeta):
    """
    Mixin for the master CQRS model, that will send data updates to it's replicas.
    """

    class Meta:
        abstract = True


class RawReplicaMixin:
    CQRS_ID = None
    CQRS_NO_DB_OPERATIONS = True
    CQRS_META = False
    CQRS_ONLY_DIRECT_SYNCS = False

    @classmethod
    def cqrs_save(cls, master_data, **kwargs):
        raise NotImplementedError

    @classmethod
    def cqrs_delete(cls, master_data, **kwargs):
        raise NotImplementedError

    @staticmethod
    def should_retry_cqrs(current_retry: int, exception=None) -> bool:
        """Checks if we should retry the message after current attempt.

        Args:
            current_retry (int): Current number of message retries.
            exception (Exception): Exception instance raised during message consume.

        Returns:
            (bool): True if message should be retried, False otherwise.
        """
        max_retries = settings.CQRS['replica']['CQRS_MAX_RETRIES']
        if max_retries is None:
            # Infinite
            return True

        return current_retry < max_retries

    @staticmethod
    def get_cqrs_retry_delay(current_retry: int) -> int:
        """Returns number of seconds to wait before requeuing the message.

        Args:
            current_retry (int): Current number of message retries.

        Returns:
            (int): Delay in seconds.
        """
        return settings.CQRS['replica']['CQRS_RETRY_DELAY']


class ReplicaMixin(RawReplicaMixin, Model, metaclass=ReplicaMeta):
    """
    Mixin for the replica CQRS model, that will receive data updates from master. Models, using
    this mixin should be readonly, but this is not enforced (f.e. for admin).
    """

    CQRS_ID = None
    """Unique CQRS identifier for all microservices."""

    CQRS_MAPPING = None
    """Mapping of master data field name to replica model field name."""

    CQRS_CUSTOM_SERIALIZATION = False
    """Set it to True to skip default data check."""

    CQRS_SELECT_FOR_UPDATE = False
    """Set it to True to acquire lock on instance creation/update."""

    CQRS_NO_DB_OPERATIONS = False
    """Set it to True to disable any default DB operations for this model."""

    CQRS_META = False
    """Set it to True to receive meta data for this model."""

    CQRS_ONLY_DIRECT_SYNCS = False
    """Set it to True to ignore broadcast sync packages and to receive only direct queue syncs."""

    objects = Manager()
    cqrs = ReplicaManager()
    """Manager that adds needed CQRS queryset methods."""

    cqrs_revision = IntegerField()
    cqrs_updated = DateTimeField()

    class Meta:
        abstract = True

    @classmethod
    def cqrs_save(
        cls,
        master_data: dict,
        previous_data: dict = None,
        sync: bool = False,
        meta: dict = None,
    ):
        """This method saves (creates or updates) model instance from CQRS master instance data.
        This method must not be overridden. Otherwise, sync checks need to be implemented manually.

        Args:
            master_data (dict): CQRS master instance data.
            previous_data (dict): Previous values for tracked fields.
            sync (bool): Sync package flag.
            meta (dict): Payload metadata, if exists.

        Returns:
            (django.db.models.Model): Model instance.
        """
        if cls.CQRS_NO_DB_OPERATIONS:
            return super().cqrs_save(master_data, previous_data=previous_data, sync=sync, meta=meta)

        return cls.cqrs.save_instance(master_data, previous_data, sync, meta)

    @classmethod
    def cqrs_create(
        cls,
        sync: bool,
        mapped_data: dict,
        previous_data: dict = None,
        meta: dict = None,
    ):
        """This method creates model instance from CQRS mapped instance data. It must be overridden
        by replicas of master models with custom serialization.

        Args:
            sync (dict): Sync package flag.
            mapped_data (dict): CQRS mapped instance data.
            previous_data (dict): Previous mapped values for tracked fields.
            meta (dict): Payload metadata, if exists.

        Returns:
            (django.db.models.Model): Model instance.
        """
        return cls._default_manager.create(**mapped_data)

    def cqrs_update(
        self,
        sync: bool,
        mapped_data: dict,
        previous_data: dict = None,
        meta: dict = None,
    ):
        """This method updates model instance from CQRS mapped instance data. It must be overridden
        by replicas of master models with custom serialization.

        Args:
            sync (dict): Sync package flag.
            mapped_data (dict): CQRS mapped instance data.
            previous_data (dict): Previous mapped values for tracked fields.
            meta (dict): Payload metadata, if exists.

        Returns:
            (django.db.models.Model): Model instance.
        """

        for key, value in mapped_data.items():
            setattr(self, key, value)
        self.save()
        return self

    @classmethod
    def cqrs_delete(cls, master_data: dict, meta: dict = None) -> bool:
        """This method deletes model instance from mapped CQRS master instance data.

        Args:
            master_data (dict): CQRS master instance data.
            meta (dict): Payload metadata, if exists.

        Returns:
            (bool): Flag, if delete operation is successful (even if nothing was deleted).
        """
        if cls.CQRS_NO_DB_OPERATIONS:
            return super().cqrs_delete(master_data, meta=meta)

        return cls.cqrs.delete_instance(master_data)
