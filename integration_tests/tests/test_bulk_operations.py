#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest

from integration_tests.tests.utils import (
    REPLICA_BASIC_TABLE, count_replica_rows, get_replica_all, get_replica_first, transport_delay,
)
from tests.dj_master.models import BasicFieldsModel


@pytest.mark.django_db(transaction=True)
def test_flow(replica_cursor):
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 0

    # Create
    master_instances = BasicFieldsModel.objects.bulk_create([
        BasicFieldsModel(
            int_field=index,
            char_field='text',
        )
        for index in range(1, 4)
    ])
    BasicFieldsModel.call_post_bulk_create(master_instances)

    transport_delay()
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 3

    assert {'text'} == {
        t[0] for t in get_replica_all(replica_cursor, REPLICA_BASIC_TABLE, ('char_field',))
    }

    # Update 1 and 2
    BasicFieldsModel.cqrs.bulk_update(
        BasicFieldsModel.objects.filter(int_field__in=(1, 2)),
        char_field='new_text',
    )

    transport_delay()
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 3

    assert ['new_text', 'new_text', 'text'] == [
        t[0] for t in get_replica_all(
            replica_cursor, REPLICA_BASIC_TABLE, ('char_field',), order_asc_by='int_field',
        )
    ]

    # Delete 1 and 3
    BasicFieldsModel.objects.filter(int_field__in=(1, 3)).delete()

    transport_delay()
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 1

    assert (2, 'new_text', 1) == get_replica_first(
        replica_cursor, REPLICA_BASIC_TABLE, ('int_field', 'char_field', 'cqrs_revision'),
    )
