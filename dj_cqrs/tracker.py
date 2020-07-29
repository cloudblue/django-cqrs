#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

from model_utils import FieldTracker
from model_utils.tracker import FieldInstanceTracker

from dj_cqrs.constants import ALL_BASIC_FIELDS, FIELDS_TRACKER_FIELD_NAME


class _CQRSTrackerInstance(FieldInstanceTracker):

    def __init__(self, instance, fields, field_map):
        super().__init__(instance, fields, field_map)
        self._attr_to_field_map = {
            f.attname: f.name
            for f in instance._meta.concrete_fields if f.is_relation
        }

    def changed(self):
        changed_fields = super().changed()
        return {
            self._attr_to_field_map.get(k, k): v
            for k, v in changed_fields.items()
        }


class CQRSTracker(FieldTracker):

    tracker_class = _CQRSTrackerInstance

    @classmethod
    def add_to_model(cls, model_cls):
        """
        Add the CQRSTracker to a model.

        :param model_cls: the model class to which add the CQRSTracker.
        :type model_cls: django.db.models.Model
        """
        opts = model_cls._meta
        fields_to_track = []
        declared = model_cls.CQRS_TRACKED_FIELDS

        for field in opts.concrete_fields:
            if declared == ALL_BASIC_FIELDS or field.name in declared:
                fields_to_track.append(
                    field.attname if field.is_relation else field.name
                )

        tracker = cls(fields=fields_to_track)
        model_cls.add_to_class(FIELDS_TRACKER_FIELD_NAME, tracker)
        tracker.finalize_class(model_cls)
