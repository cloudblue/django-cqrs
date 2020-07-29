#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest
from django.utils.timezone import now

from integration_tests.tests.utils import (
    REPLICA_BASIC_TABLE, count_replica_rows, get_replica_first, transport_delay,
)
from tests.dj_master.models import BasicFieldsModel


@pytest.mark.django_db(transaction=True)
def test_flow(replica_cursor):
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 0

    # Create
    master_instance = BasicFieldsModel.objects.create(
        int_field=1,
        char_field='text',
        date_field=now().date(),
        bool_field=False,
    )
    assert master_instance.cqrs_revision == 0

    transport_delay()
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 1

    replica_tuple = get_replica_first(
        replica_cursor, REPLICA_BASIC_TABLE,
        ('int_field', 'char_field', 'date_field', 'cqrs_revision', 'cqrs_updated', 'bool_field'),
    )
    assert (
        master_instance.int_field,
        master_instance.char_field,
        master_instance.date_field,
        master_instance.cqrs_revision,
        master_instance.cqrs_updated,
        master_instance.bool_field,
    ) == replica_tuple

    # Update
    master_instance.bool_field = True
    master_instance.save()

    if hasattr(master_instance, 'get_tracked_fields_data'):
        previous_values = master_instance.get_tracked_fields_data()
        assert 'bool_field' in previous_values
        assert previous_values['bool_field'] is False

    master_instance.refresh_from_db()
    assert master_instance.cqrs_revision == 1

    transport_delay()
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 1

    updated_replica_tuple = get_replica_first(
        replica_cursor, REPLICA_BASIC_TABLE,
        ('int_field', 'cqrs_revision', 'cqrs_updated', 'bool_field'),
    )
    assert (
       master_instance.int_field,
       master_instance.cqrs_revision,
       master_instance.cqrs_updated,
       master_instance.bool_field,
    ) == updated_replica_tuple

    # Delete
    master_instance.delete()
    transport_delay()
    assert count_replica_rows(replica_cursor, REPLICA_BASIC_TABLE) == 0
