from __future__ import unicode_literals

import six
from django.db import DatabaseError


def assert_is_sub_dict(dict1, dict2):
    assert six.viewitems(dict1) <= six.viewitems(dict2)


def assert_publisher_once_called_with_args(publisher_mock, *args):
    publisher_mock.call_count = 1
    call_t_payload = publisher_mock.call_args[0][0]

    assert call_t_payload.signal_type == args[0]
    assert call_t_payload.cqrs_id == args[1]
    assert call_t_payload.pk == args[3]
    assert_is_sub_dict(args[2], call_t_payload.instance_data)

    required_fields = {'cqrs_revision', 'cqrs_updated'}
    assert not (required_fields - set(call_t_payload.instance_data.keys()))


def db_error(*args, **kwargs):
    raise DatabaseError()
