from __future__ import unicode_literals

from itertools import chain

import six
from django.db.models import DateTimeField, F, IntegerField, Manager, Model

from dj_cqrs.constants import ALL_BASIC_FIELDS
from dj_cqrs.managers import MasterManager, ReplicaManager
from dj_cqrs.metas import MasterMeta, ReplicaMeta
from dj_cqrs.signals import MasterSignals, post_bulk_create, post_update


class MasterMixin(six.with_metaclass(MasterMeta, Model)):
    """
    Mixin for the master CQRS model, that will send data updates to it's replicas.

    CQRS_FIELDS - Fields, that need to by synchronized between microservices.
    CQRS_ID - Unique CQRS identifier for all microservices.
    cqrs - Manager, that adds needed CQRS queryset methods.
    """
    CQRS_FIELDS = ALL_BASIC_FIELDS
    CQRS_ID = None

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

    def to_cqrs_dict(self):
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
        for cqrs_tech_field_name in ('cqrs_revision', 'cqrs_updated'):
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


class ReplicaMixin(six.with_metaclass(ReplicaMeta, Model)):
    """
    Mixin for the replica CQRS model, that will receive data updates from master. Models, using
    this mixin should be readonly, but this is not enforced (f.e. for admin).

    CQRS_ID - Unique CQRS identifier for all microservices.
    CQRS_MAPPING - Mapping of master data field name to replica model field name.
    """
    CQRS_ID = None
    CQRS_MAPPING = None

    objects = Manager()
    cqrs = ReplicaManager()

    cqrs_revision = IntegerField()
    cqrs_updated = DateTimeField()

    class Meta:
        abstract = True

    @classmethod
    def cqrs_save(cls, master_data):
        """ This method saves (creates or updates) model instance from CQRS master instance data.

        :param dict master_data: CQRS master instance data.
        :return: Model instance.
        :rtype: django.db.models.Model
        """
        return cls.cqrs.save_instance(master_data)

    @classmethod
    def cqrs_delete(cls, master_data):
        """ This method deletes model instance from mapped CQRS master instance data.

        :param dict master_data: CQRS master instance data.
        :return: Flag, if delete operation is successful (even if nothing was deleted).
        :rtype: bool
        """
        return cls.cqrs.delete_instance(master_data)
