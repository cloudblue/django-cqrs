#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest

from integration_tests.tests.utils import (
    REPLICA_BASIC_TABLE, count_replica_rows, get_replica_first, transport_delay,
)
from tests.dj_master.models import BasicFieldsModel


@pytest.mark.django_db(transaction=True)
def test_flow(replica_cursor, mocker):
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 0

    # Create
    master_instance = BasicFieldsModel.objects.create(
        int_field=1,
        char_field='text',
    )
    assert master_instance.cqrs_revision == 0

    transport_delay()
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 1

    replica_tuple = get_replica_first(
        replica_cursor, REPLICA_BASIC_TABLE,
        ('int_field', 'char_field', 'cqrs_revision', 'cqrs_updated'),
    )
    assert (
        master_instance.int_field,
        master_instance.char_field,
        master_instance.cqrs_revision,
        master_instance.cqrs_updated,
    ) == replica_tuple

    # We simulate transport error
    mocker.patch('dj_cqrs.controller.producer.produce')
    master_instance.char_field = 'new'
    master_instance.save()
    mocker.stopall()

    master_instance.refresh_from_db()
    assert master_instance.cqrs_revision == 1

    # Sync to other service
    master_instance.cqrs_sync(queue='other_replica')

    transport_delay()
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 1

    replica_tuple = get_replica_first(
        replica_cursor, REPLICA_BASIC_TABLE,
        ('int_field', 'char_field', 'cqrs_revision', 'cqrs_updated'),
    )
    assert replica_tuple[0] == 1
    assert replica_tuple[1] == 'text'
    assert replica_tuple[2] == 0

    # Sync to replica
    master_instance.cqrs_sync(queue='replica')

    transport_delay()
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 1

    replica_tuple = get_replica_first(
        replica_cursor, REPLICA_BASIC_TABLE,
        ('int_field', 'char_field', 'cqrs_revision', 'cqrs_updated'),
    )
    assert replica_tuple[0] == 1
    assert replica_tuple[1] == 'new'
    assert replica_tuple[2] == 1

    mocker.patch('dj_cqrs.controller.producer.produce')
    master_instance.char_field = 'new2'
    master_instance.save()
    mocker.stopall()

    # Sync to all
    master_instance.cqrs_sync()

    transport_delay()
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 1

    replica_tuple = get_replica_first(
        replica_cursor, REPLICA_BASIC_TABLE,
        ('int_field', 'char_field', 'cqrs_revision', 'cqrs_updated'),
    )
    assert replica_tuple[0] == 1
    assert replica_tuple[1] == 'new2'
    assert replica_tuple[2] == 2
