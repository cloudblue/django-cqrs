import logging

from django.conf import settings
from django.db import OperationalError, transaction

from dj_cqrs.constants import (
    DB_VENDOR_MYSQL,
    DB_VENDOR_PG,
    MYSQL_TIMEOUT_ERROR_CODE,
    PG_TIMEOUT_FLAG,
    SUPPORTED_TIMEOUT_DB_VENDORS,
)


def install_last_query_capturer(model_cls):
    conn = _connection(model_cls)
    if not _get_last_query_capturer(conn):
        conn.execute_wrappers.append(_LastQueryCaptureWrapper())


def log_timed_out_queries(error, model_cls):  # pragma: no cover
    log_q = bool(settings.CQRS['replica'].get('CQRS_LOG_TIMED_OUT_QUERIES', False))
    if not (log_q and isinstance(error, OperationalError) and error.args):
        return

    conn = _connection(model_cls)
    conn_vendor = getattr(conn, 'vendor', '')
    if conn_vendor not in SUPPORTED_TIMEOUT_DB_VENDORS:
        return

    e_arg = error.args[0]
    is_timeout_error = bool(
        (conn_vendor == DB_VENDOR_MYSQL and e_arg == MYSQL_TIMEOUT_ERROR_CODE)
        or (conn_vendor == DB_VENDOR_PG and isinstance(e_arg, str) and PG_TIMEOUT_FLAG in e_arg)
    )
    if is_timeout_error:
        query = getattr(_get_last_query_capturer(conn), 'query', None)
        if query:
            logger_name = settings.CQRS['replica'].get('CQRS_QUERY_LOGGER', '') or 'django-cqrs'
            logger = logging.getLogger(logger_name)
            logger.error('Timed out query:\n%s', query)


class _LastQueryCaptureWrapper:
    def __init__(self):
        self.query = None

    def __call__(self, execute, sql, params, many, context):
        try:
            execute(sql, params, many, context)
        finally:
            self.query = sql


def _get_last_query_capturer(conn):
    return next((w for w in conn.execute_wrappers if isinstance(w, _LastQueryCaptureWrapper)), None)


def _connection(model_cls):
    return transaction.get_connection(using=model_cls._default_manager.db)
