#  Copyright © 2022 Ingram Micro Inc. All rights reserved.

import logging

from django.core.exceptions import ValidationError
from django.db import Error, transaction
from django.db.models import F, Manager
from django.utils import timezone

from dj_cqrs.constants import FIELDS_TRACKER_FIELD_NAME, TRACKED_FIELDS_ATTR_NAME


logger = logging.getLogger('django-cqrs')


class MasterManager(Manager):
    def bulk_create(self, objs, **kwargs):
        """
        Custom bulk create method to support sending of create signals.
        This can be used only in cases, when IDs are generated on client or DB returns IDs.

        :param django.db.models.Model objs: List of objects for creation
        :param kwargs: Bulk create kwargs
        """
        for obj in objs:
            obj.save_tracked_fields()
        objs = super().bulk_create(objs, **kwargs)

        if objs:
            self.model.call_post_bulk_create(objs, using=self.db)

        return objs

    def bulk_update(self, queryset, **kwargs):
        """ Custom update method to support sending of update signals.

        :param django.db.models.QuerySet queryset: Django Queryset (f.e. filter)
        :param kwargs: Update kwargs
        """
        prev_data_mapper = {}
        collect_prev_data = hasattr(self.model, FIELDS_TRACKER_FIELD_NAME)

        def list_all():
            return list(queryset.all())

        with transaction.atomic(savepoint=False):
            if collect_prev_data:
                objs = list_all()
                if not objs:
                    return

                for obj in objs:
                    prev_data_mapper[obj.pk] = getattr(obj, FIELDS_TRACKER_FIELD_NAME).current()

            current_dt = timezone.now()
            result = queryset.update(
                cqrs_revision=F('cqrs_revision') + 1, cqrs_updated=current_dt, **kwargs,
            )

            objs = list_all()
            if collect_prev_data:
                for obj in objs:
                    setattr(obj, TRACKED_FIELDS_ATTR_NAME, prev_data_mapper.get(obj.pk))

        queryset.model.call_post_update(objs, using=queryset.db)

        return result


class ReplicaManager(Manager):
    def save_instance(self, master_data, previous_data=None, sync=False, meta=None):
        """ This method saves (creates or updates) model instance from CQRS master instance data.

        :param dict master_data: CQRS master instance data.
        :param dict previous_data: Previous values for tracked fields.
        :param bool sync: Sync package flag.
        :param dict or None meta: Payload metadata, if exists.
        :return: Model instance.
        :rtype: django.db.models.Model
        """
        mapped_data = self._map_save_data(master_data)
        mapped_previous_data = self._map_previous_data(previous_data) if previous_data else None
        if mapped_data:
            pk_name = self._get_model_pk_name()
            pk_value = mapped_data[pk_name]
            f_kwargs = {pk_name: pk_value}

            qs = self.model._default_manager.filter(**f_kwargs).order_by()
            if self.model.CQRS_SELECT_FOR_UPDATE:
                qs = qs.select_for_update()

            instance = qs.first()

            if instance:
                return self.update_instance(
                    instance,
                    mapped_data,
                    previous_data=mapped_previous_data,
                    sync=sync,
                    meta=meta,
                )

            return self.create_instance(
                mapped_data,
                previous_data=mapped_previous_data,
                sync=sync,
                meta=meta,
            )

    def create_instance(self, mapped_data, previous_data=None, sync=False, meta=None):
        """ This method creates model instance from mapped CQRS master instance data.

        :param dict mapped_data: Mapped CQRS master instance data.
        :param dict previous_data: Previous values for tracked fields.
        :param bool sync: Sync package flag.
        :param dict or None meta: Payload metadata, if exists.
        :return: ReplicaMixin model instance.
        :rtype: django.db.models.Model
        """
        f_kw = {'previous_data': previous_data}
        if self.model.CQRS_META:
            f_kw['meta'] = meta

        try:
            return self.model.cqrs_create(sync, mapped_data, **f_kw)
        except (Error, ValidationError) as e:
            pk_value = mapped_data[self._get_model_pk_name()]

            logger.error(
                '{0}\nCQRS create error: pk = {1} ({2}).'.format(
                    str(e), pk_value, self.model.CQRS_ID,
                ),
            )

    def update_instance(self, instance, mapped_data, previous_data=None, sync=False, meta=None):
        """ This method updates model instance from mapped CQRS master instance data.

        :param django.db.models.Model instance: ReplicaMixin model instance.
        :param dict mapped_data: Mapped CQRS master instance data.
        :param dict previous_data: Previous values for tracked fields.
        :param dict or None meta: Payload metadata, if exists.
        :param bool sync: Sync package flag.
        :return: ReplicaMixin model instance.
        :rtype: django.db.models.Model
        """
        pk_value = mapped_data[self._get_model_pk_name()]
        current_cqrs_revision = mapped_data['cqrs_revision']
        existing_cqrs_revision = instance.cqrs_revision

        if sync:
            if existing_cqrs_revision > current_cqrs_revision:
                w_tpl = (
                    'CQRS revision downgrade on sync: pk = {0}, '
                    'cqrs_revision = new {1} / existing {2} ({3}).'
                )
                logger.warning(w_tpl.format(
                    pk_value, current_cqrs_revision, existing_cqrs_revision, self.model.CQRS_ID,
                ))

        else:
            if existing_cqrs_revision > current_cqrs_revision:
                e_tpl = (
                    'Wrong CQRS sync order: pk = {0}, '
                    'cqrs_revision = new {1} / existing {2} ({3}).'
                )
                logger.error(e_tpl.format(
                    pk_value, current_cqrs_revision, existing_cqrs_revision, self.model.CQRS_ID,
                ))
                return instance

            if existing_cqrs_revision == current_cqrs_revision:
                logger.error(
                    'Received duplicate CQRS data: pk = {0}, cqrs_revision = {1} ({2}).'.format(
                        pk_value, current_cqrs_revision, self.model.CQRS_ID,
                    ),
                )
                if current_cqrs_revision == 0:
                    logger.warning(
                        'CQRS potential creation race condition: pk = {0} ({1}).'.format(
                            pk_value, self.model.CQRS_ID,
                        ),
                    )

                return instance

            if current_cqrs_revision != instance.cqrs_revision + 1:
                w_tpl = (
                    'Lost or filtered out {0} CQRS packages: pk = {1}, cqrs_revision = {2} ({3})'
                )
                logger.warning(w_tpl.format(
                    current_cqrs_revision - instance.cqrs_revision - 1,
                    pk_value, current_cqrs_revision, self.model.CQRS_ID,
                ))

        f_kw = {'previous_data': previous_data}
        if self.model.CQRS_META:
            f_kw['meta'] = meta

        try:
            return instance.cqrs_update(sync, mapped_data, **f_kw)
        except (Error, ValidationError) as e:
            logger.error(
                '{0}\nCQRS update error: pk = {1}, cqrs_revision = {2} ({3}).'.format(
                    str(e), pk_value, current_cqrs_revision, self.model.CQRS_ID,
                ),
            )

    def delete_instance(self, master_data):
        """ This method deletes model instance from mapped CQRS master instance data.

        :param dict master_data: CQRS master instance data.
        :return: Flag, if delete operation is successful (even if nothing was deleted).
        :rtype: bool
        """
        mapped_data = self._map_delete_data(master_data)

        if mapped_data:
            pk_name = self._get_model_pk_name()
            pk_value = mapped_data[pk_name]
            try:
                self.model._default_manager.filter(**{pk_name: pk_value}).delete()
                return True
            except Error as e:
                logger.error(
                    '{0}\nCQRS delete error: pk = {1} ({2}).'.format(
                        str(e), pk_value, self.model.CQRS_ID,
                    ),
                )

        return False

    def _map_previous_data(self, previous_data):
        if self.model.CQRS_MAPPING is None:
            return previous_data

        mapped_previous_data = {}

        for master_name, replica_name in self.model.CQRS_MAPPING.items():
            if master_name not in previous_data:
                continue

            mapped_previous_data[replica_name] = previous_data[master_name]
        mapped_previous_data = self._remove_excessive_data(mapped_previous_data)
        return mapped_previous_data

    def _map_save_data(self, master_data):
        if not self._cqrs_fields_are_filled(master_data):
            return

        mapped_data = self._make_initial_mapping(master_data)
        if not mapped_data:
            return

        if self._get_model_pk_name() not in mapped_data:
            self._log_pk_data_error()
            return

        if self.model.CQRS_CUSTOM_SERIALIZATION:
            return mapped_data

        mapped_data = self._remove_excessive_data(mapped_data)

        if self._all_required_fields_are_filled(mapped_data):
            return mapped_data

    def _make_initial_mapping(self, master_data):
        if self.model.CQRS_MAPPING is None:
            return master_data

        mapped_data = {
            'cqrs_revision': master_data['cqrs_revision'],
            'cqrs_updated': master_data['cqrs_updated'],
        }
        for master_name, replica_name in self.model.CQRS_MAPPING.items():
            if master_name not in master_data:
                logger.error('Bad master-replica mapping for {0} ({1}).'.format(
                    master_name, self.model.CQRS_ID,
                ))
                return

            mapped_data[replica_name] = master_data[master_name]
        return mapped_data

    def _remove_excessive_data(self, data):
        opts = self.model._meta
        possible_field_names = {
            f.name for f in opts.fields
        }
        return {k: v for k, v in data.items() if k in possible_field_names}

    def _all_required_fields_are_filled(self, mapped_data):
        opts = self.model._meta

        required_field_names = {
            f.name for f in opts.fields if not f.null
        }
        if not (required_field_names - set(mapped_data.keys())):
            return True

        logger.error(
            'Not all required CQRS fields are provided in data ({0}).'.format(self.model.CQRS_ID),
        )
        return False

    def _map_delete_data(self, master_data):
        if 'id' not in master_data:
            self._log_pk_data_error()
            return

        if not self._cqrs_fields_are_filled(master_data):
            return

        return {
            self._get_model_pk_name(): master_data['id'],
            'cqrs_revision': master_data['cqrs_revision'],
            'cqrs_updated': master_data['cqrs_updated'],
        }

    def _cqrs_fields_are_filled(self, data):
        if 'cqrs_revision' in data and 'cqrs_updated' in data:
            return True

        logger.error('CQRS sync fields are not provided in data ({0}).'.format(self.model.CQRS_ID))
        return False

    def _log_pk_data_error(self):
        logger.error('CQRS PK is not provided in data ({0}).'.format(self.model.CQRS_ID))

    def _get_model_pk_name(self):
        return self.model._meta.pk.name
