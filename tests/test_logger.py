import logging

import pytest
from django.db import (
    DatabaseError,
    IntegrityError,
    OperationalError,
    connection,
)

from dj_cqrs.logger import (
    _LastQueryCaptureWrapper,
    install_last_query_capturer,
    log_timed_out_queries,
)
from tests.dj_replica import models


@pytest.mark.django_db(transaction=True)
def test_install_last_query_capturer():
    for _ in range(2):
        install_last_query_capturer(models.AuthorRef)

        assert len(connection.execute_wrappers) == 1
        assert isinstance(connection.execute_wrappers[0], _LastQueryCaptureWrapper)

    with connection.cursor() as c:
        c.execute('SELECT 1')

    assert connection.execute_wrappers[0].query == 'SELECT 1'

    connection.execute_wrappers.pop()


def test_log_timed_out_queries_not_supported(caplog):
    assert log_timed_out_queries(None, None) is None
    assert not caplog.record_tuples


@pytest.mark.parametrize(
    'error',
    [
        IntegrityError('some error'),
        DatabaseError(),
        OperationalError(),
    ],
)
def test_log_timed_out_queries_other_error(error, settings, caplog):
    settings.CQRS_LOG_TIMED_OUT_QUERIES = 1

    assert log_timed_out_queries(error, None) is None
    assert not caplog.record_tuples


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    'engine, error, l_name, records',
    [
        ('sqlite', None, None, []),
        (
            'postgres',
            OperationalError('canceling statement due to statement timeout'),
            None,
            [
                (
                    'django-cqrs',
                    logging.ERROR,
                    'Timed out query:\nSELECT 1',
                )
            ],
        ),
        (
            'postgres',
            OperationalError('canceling statement due to statement timeout'),
            'long-query',
            [
                (
                    'long-query',
                    logging.ERROR,
                    'Timed out query:\nSELECT 1',
                )
            ],
        ),
        (
            'postgres',
            OperationalError('could not connect to server'),
            None,
            [],
        ),
        (
            'postgres',
            OperationalError(125, 'Some error'),
            None,
            [],
        ),
        (
            'mysql',
            OperationalError(3024),
            None,
            [
                (
                    'django-cqrs',
                    logging.ERROR,
                    'Timed out query:\nSELECT 1',
                )
            ],
        ),
        (
            'mysql',
            OperationalError(
                3024, 'Query exec was interrupted, max statement execution time exceeded'
            ),
            'long-query-1',
            [
                (
                    'long-query-1',
                    logging.ERROR,
                    'Timed out query:\nSELECT 1',
                )
            ],
        ),
        (
            'mysql',
            OperationalError(1040, 'Too many connections'),
            None,
            [],
        ),
    ],
)
def test_apply_query_timeouts(settings, engine, l_name, error, records, caplog):
    if settings.DB_ENGINE != engine:
        return

    settings.CQRS['replica']['CQRS_LOG_TIMED_OUT_QUERIES'] = True
    settings.CQRS['replica']['CQRS_QUERY_LOGGER'] = l_name

    model_cls = models.BasicFieldsModelRef
    install_last_query_capturer(model_cls)

    with connection.cursor() as c:
        c.execute('SELECT 1')

    assert log_timed_out_queries(error, model_cls) is None
    assert caplog.record_tuples == records

    connection.execute_wrappers.pop()
