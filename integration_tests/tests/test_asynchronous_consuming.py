#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest

from integration_tests.tests.utils import (
    REPLICA_BASIC_TABLE, REPLICA_EVENT_TABLE,
    count_replica_rows, get_replica_all, transport_delay,
)
from tests.dj_master.models import BasicFieldsModel


@pytest.mark.django_db(transaction=True)
def test_both_consumers_consume(replica_cursor):
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 0
    assert count_replica_rows(replica_cursor, REPLICA_EVENT_TABLE) == 0

    master_instances = BasicFieldsModel.objects.bulk_create([
        BasicFieldsModel(
            int_field=index,
            char_field='text',
        )
        for index in range(1, 10)
    ])
    BasicFieldsModel.call_post_bulk_create(master_instances)

    transport_delay(3)
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 9
    assert count_replica_rows(replica_cursor, REPLICA_EVENT_TABLE) == 9

    events_data = get_replica_all(replica_cursor, REPLICA_EVENT_TABLE, ('pid', ),)
    assert len({d[0] for d in events_data}) == 2


@pytest.mark.django_db(transaction=True)
def test_de_duplication(replica_cursor):
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 0
    assert count_replica_rows(replica_cursor, REPLICA_EVENT_TABLE) == 0

    master_instance = BasicFieldsModel.objects.create(int_field=1, char_field='text')
    BasicFieldsModel.call_post_bulk_create([master_instance for _ in range(9)])

    transport_delay(3)
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 1
    assert count_replica_rows(replica_cursor, REPLICA_EVENT_TABLE) == 10
