#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import six
from django.db import DatabaseError


def assert_is_sub_dict(dict1, dict2):
    assert six.viewitems(dict1) <= six.viewitems(dict2)


def assert_publisher_once_called_with_args(publisher_mock, *args):
    assert publisher_mock.call_count == 1
    call_t_payload = publisher_mock.call_args[0][0]

    assert call_t_payload.signal_type == args[0]
    assert call_t_payload.cqrs_id == args[1]
    assert call_t_payload.pk == args[3]
    assert_is_sub_dict(args[2], call_t_payload.instance_data)

    required_fields = {'cqrs_revision', 'cqrs_updated'}
    assert not (required_fields - set(call_t_payload.instance_data.keys()))


def db_error(*args, **kwargs):
    raise DatabaseError()


def assert_tracked_fields(model_cls, fields):
    if model_cls.CQRS_TRACKED_FIELDS == '__all__':
        fields_to_track = {
            f.attname if f.is_relation else f.name
            for f in model_cls._meta.concrete_fields
        }
    else:
        fields_to_track = set()
        for fname in model_cls.CQRS_TRACKED_FIELDS:
            field = model_cls._meta.get_field(fname)
            if field.is_relation:
                fields_to_track.add(field.attname)
            else:
                fields_to_track.add(field.name)

    assert fields_to_track == fields
