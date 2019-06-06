from __future__ import unicode_literals

import time

import pytest
import sqlite3

from tests.dj_master.models import BasicFieldsModel


@pytest.fixture
def replica_cursor():
    connection = sqlite3.connect('./db/replica_db.sqlite3')
    cursor = connection.cursor()
    yield cursor


def count_replica_rows(cursor, table):
    return list(cursor.execute('SELECT COUNT(*) FROM {}'.format(table)))[0][0]


@pytest.mark.django_db
def test_flow_for_simple_models(caplog, replica_cursor):
    assert count_replica_rows(replica_cursor, 'dj_replica_basicfieldsmodelref') == 0

    BasicFieldsModel.objects.create(
        int_field=1,
        char_field='text',
    )

    time.sleep(2)

    assert count_replica_rows(replica_cursor, 'dj_replica_basicfieldsmodelref') == 1
