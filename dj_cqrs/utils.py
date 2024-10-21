#  Copyright © 2024 Ingram Micro Inc. All rights reserved.

import logging
from collections import defaultdict
from contextlib import ContextDecorator
from datetime import date, datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from dj_cqrs.constants import DB_VENDOR_PG, SUPPORTED_TIMEOUT_DB_VENDORS
from dj_cqrs.logger import install_last_query_capturer
from dj_cqrs.state import cqrs_state


logger = logging.getLogger('django-cqrs')


def get_message_expiration_dt(message_ttl=None):
    """Calculates when message should expire.

    :param int or None message_ttl:
    :return: Expiration datetime or None if infinite
    :rtype: datetime.datetime or None
    """
    message_ttl = message_ttl or settings.CQRS['master']['CQRS_MESSAGE_TTL']
    if message_ttl is None:
        # Infinite
        return

    return timezone.now() + timedelta(seconds=message_ttl)


def get_delay_queue_max_size():
    """Returns max allowed number of "waiting" messages in the delay queue.

    :return: Positive integer number or None if infinite
    :rtype: int
    """
    if 'replica' not in settings.CQRS:
        return None

    return settings.CQRS['replica']['delay_queue_max_size']


def get_messages_prefetch_count_per_worker():
    """Returns max allowed number of unacked messages, that can be consumed by a single worker.

    :return: Positive integer number or 0 if infinite
    :rtype: int
    """
    delay_queue_max_size = get_delay_queue_max_size()
    if delay_queue_max_size is None:
        # Infinite
        return 0

    return delay_queue_max_size + 1


def get_json_valid_value(value):
    return str(value) if isinstance(value, (date, datetime, UUID)) else value


def apply_query_timeouts(model_cls):  # pragma: no cover
    query_timeout = int(settings.CQRS['replica'].get('CQRS_QUERY_TIMEOUT', 0))
    if query_timeout <= 0:
        return

    model_db = model_cls._default_manager.db
    conn = transaction.get_connection(using=model_db)
    conn_vendor = getattr(conn, 'vendor', '')
    if conn_vendor not in SUPPORTED_TIMEOUT_DB_VENDORS:
        return

    if conn_vendor == DB_VENDOR_PG:
        statement = 'SET statement_timeout TO %s'
    else:
        statement = 'SET SESSION MAX_EXECUTION_TIME=%s'

    with conn.cursor() as cursor:
        cursor.execute(statement, params=(query_timeout,))

    install_last_query_capturer(model_cls)


class _BulkRelateCM(ContextDecorator):
    def __init__(self, cqrs_id=None):
        self._cqrs_id = cqrs_id
        self._mapping = defaultdict(lambda: defaultdict(set))
        self._cache = {}

    def register(self, instance, using=None):
        instance_cqrs_id = getattr(instance, 'CQRS_ID', None)
        if (not instance_cqrs_id) or (self._cqrs_id and instance_cqrs_id != self._cqrs_id):
            return

        self._mapping[instance_cqrs_id][using].add(instance.pk)

    def get_cached_instance(self, instance, using=None):
        instance_cqrs_id = getattr(instance, 'CQRS_ID', None)
        if (not instance_cqrs_id) or (self._cqrs_id and instance_cqrs_id != self._cqrs_id):
            return

        instance_pk = instance.pk
        cached_instances = self._cache.get(instance_cqrs_id, {}).get(using, {})
        if cached_instances:
            return cached_instances.get(instance_pk)

        cached_pks = self._mapping[instance_cqrs_id][using]
        if not cached_pks:
            return

        qs = instance.__class__._default_manager.using(using)
        instances_cache = {
            instance.pk: instance
            for instance in instance.__class__.relate_cqrs_serialization(qs)
            .filter(
                pk__in=cached_pks,
            )
            .order_by()
            .all()
        }
        self._cache.update(
            {
                instance_cqrs_id: {
                    using: instances_cache,
                },
            }
        )
        return instances_cache.get(instance_pk)

    def __enter__(self):
        cqrs_state.bulk_relate_cm = self

    def __exit__(self, exc_type, exc_val, exc_tb):
        cqrs_state.bulk_relate_cm = None


def bulk_relate_cqrs_serialization(cqrs_id=None):
    return _BulkRelateCM(cqrs_id=cqrs_id)
