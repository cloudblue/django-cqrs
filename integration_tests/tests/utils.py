#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import time


REPLICA_BASIC_TABLE = 'dj_replica_basicfieldsmodelref'
REPLICA_EVENT_TABLE = 'dj_replica_event'

REPLICA_TABLES = (REPLICA_BASIC_TABLE, REPLICA_EVENT_TABLE)


def count_replica_rows(cursor, table):
    cursor.execute('SELECT COUNT(*) FROM {};'.format(table))
    return cursor.fetchone()[0]


def get_replica_all(cursor, table, columns=None, order_asc_by=None):
    select = ','.join(columns) if columns else '*'

    sql = 'SELECT {} FROM {}'.format(select, table)
    if order_asc_by:
        sql = '{} ORDER BY {} ASC;'.format(sql, order_asc_by)

    cursor.execute(sql)
    return cursor.fetchall()


def get_replica_first(cursor, table, columns=None):
    select = ','.join(columns) if columns else '*'

    cursor.execute('SELECT {} FROM {} LIMIT 1;'.format(select, table))
    return cursor.fetchone()


def transport_delay(delay=1):
    time.sleep(delay)
