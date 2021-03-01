#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest

from integration_tests.tests.utils import (
    REPLICA_BASIC_TABLE, REPLICA_EVENT_TABLE,
    count_replica_rows, get_replica_all, transport_delay,
)
from tests.dj_master.models import BasicFieldsModel


@pytest.mark.django_db(transaction=True)
def test_both_consumers_consume(settings, replica_cursor, clean_rabbit_transport_connection):
    settings.CQRS['MESSAGE_TTL'] = '4000'
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

    transport_delay(5)
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 9
    assert count_replica_rows(replica_cursor, REPLICA_EVENT_TABLE) == 9

    events_data = get_replica_all(replica_cursor, REPLICA_EVENT_TABLE, ('pid', ),)
    assert len({d[0] for d in events_data}) == 2


@pytest.mark.django_db(transaction=True)
def test_de_duplication(settings, replica_cursor, clean_rabbit_transport_connection):
    settings.CQRS['MESSAGE_TTL'] = '4000'
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 0
    assert count_replica_rows(replica_cursor, REPLICA_EVENT_TABLE) == 0

    master_instance = BasicFieldsModel.objects.create(int_field=21, char_field='text')
    BasicFieldsModel.call_post_bulk_create([master_instance])
    transport_delay(5)

    replica_cursor.execute('TRUNCATE TABLE {};'.format(REPLICA_EVENT_TABLE))
    BasicFieldsModel.call_post_bulk_create([master_instance for _ in range(10)])

    transport_delay(5)
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 1
    assert count_replica_rows(replica_cursor, REPLICA_EVENT_TABLE) == 10
