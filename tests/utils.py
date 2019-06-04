from __future__ import unicode_literals

import six


def assert_is_sub_dict(dict1, dict2):
    assert six.viewitems(dict1) <= six.viewitems(dict2)


def assert_publisher_once_called_with_args(publisher_mock, *args):
    publisher_mock.call_count = 1
    call_args = publisher_mock.call_args[0]

    assert call_args[0] == args[0]
    assert call_args[1] == args[1]
    assert_is_sub_dict(args[2], call_args[2])
