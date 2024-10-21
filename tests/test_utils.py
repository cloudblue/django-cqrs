#  Copyright © 2023 Ingram Micro Inc. All rights reserved.

from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)
from unittest.mock import patch
from uuid import UUID

import pytest
from django.db import transaction

from dj_cqrs.state import cqrs_state
from dj_cqrs.utils import (
    apply_query_timeouts,
    bulk_relate_cqrs_serialization,
    get_delay_queue_max_size,
    get_json_valid_value,
    get_message_expiration_dt,
    get_messages_prefetch_count_per_worker,
)
from tests.dj_master import models as master_models
from tests.dj_replica import models


def test_get_message_expiration_dt_fixed(mocker, settings):
    settings.CQRS['master']['CQRS_MESSAGE_TTL'] = 3600
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('django.utils.timezone.now', return_value=fake_now)

    result = get_message_expiration_dt()

    expected_result = fake_now + timedelta(seconds=3600)
    assert result == expected_result


def test_get_message_expiration_dt_fixed_from_parameter(mocker, settings):
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('django.utils.timezone.now', return_value=fake_now)

    result = get_message_expiration_dt(message_ttl=2200)

    expected_result = fake_now + timedelta(seconds=2200)
    assert result == expected_result


def test_get_message_expiration_dt_infinite(mocker, settings):
    settings.CQRS['master']['CQRS_MESSAGE_TTL'] = None
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('django.utils.timezone.now', return_value=fake_now)

    result = get_message_expiration_dt()

    assert result is None


def test_get_delay_queue_max_size_master(settings):
    del settings.CQRS['replica']

    assert get_delay_queue_max_size() is None


def test_get_delay_queue_max_size_replica(settings):
    settings.CQRS['replica']['delay_queue_max_size'] = 4

    assert get_delay_queue_max_size() == 4


def test_get_messaged_prefetch_count_per_worker_no_delay_queue(settings):
    settings.CQRS['replica']['delay_queue_max_size'] = None

    assert get_messages_prefetch_count_per_worker() == 0


def test_get_messaged_prefetch_count_per_worker_with_delay_queue(settings):
    settings.CQRS['replica']['delay_queue_max_size'] = 4

    assert get_messages_prefetch_count_per_worker() == 5


@pytest.mark.parametrize(
    'value,result',
    (
        (None, None),
        (1, 1),
        (datetime(2022, 1, 1, second=0, tzinfo=timezone.utc), '2022-01-01 00:00:00+00:00'),
        (date(2022, 2, 1), '2022-02-01'),
        (UUID('0419d87b-d477-44e4-82c4-310f56faa3c7'), '0419d87b-d477-44e4-82c4-310f56faa3c7'),
        ('abc', 'abc'),
    ),
)
def test_get_json_valid_value(value, result):
    assert get_json_valid_value(value) == result


@pytest.mark.django_db
@pytest.mark.parametrize(
    'engine, p_count',
    [
        ('sqlite', 0),
        ('postgres', 1),
        ('mysql', 1),
    ],
)
def test_apply_query_timeouts(settings, engine, p_count):
    if settings.DB_ENGINE != engine:
        return

    settings.CQRS['replica']['CQRS_QUERY_TIMEOUT'] = 1
    with patch('dj_cqrs.utils.install_last_query_capturer') as p:
        assert apply_query_timeouts(models.BasicFieldsModelRef) is None

    assert p.call_count == p_count


@pytest.mark.django_db(transaction=True)
def test_bulk_relate_cqrs_serialization_simple_model(mocker):
    produce_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    @bulk_relate_cqrs_serialization()
    def func():
        assert cqrs_state.bulk_relate_cm

        instance = master_models.SimplestModel(id=1)
        instance.save()

    assert cqrs_state.bulk_relate_cm is None
    func()

    assert master_models.SimplestModel.objects.count() == 1
    assert produce_mock.call_count == 1
    assert cqrs_state.bulk_relate_cm is None


@pytest.mark.django_db(transaction=True)
def test_bulk_relate_cqrs_serialization_serialized_model(mocker):
    produce_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    assert cqrs_state.bulk_relate_cm is None
    with bulk_relate_cqrs_serialization(cqrs_id=master_models.Author.CQRS_ID):
        bulk_relate_cm = cqrs_state.bulk_relate_cm

        with transaction.atomic(savepoint=False):
            master_models.Author.objects.create(id=1)

            assert bulk_relate_cm
            assert bulk_relate_cm._mapping
            assert not bulk_relate_cm._cache

        assert bulk_relate_cm._cache

    assert master_models.Author.objects.count() == 1
    assert produce_mock.call_count == 1
    assert cqrs_state.bulk_relate_cm is None


def test_bulk_relate_cqrs_serialization_error():
    assert cqrs_state.bulk_relate_cm is None

    try:
        with bulk_relate_cqrs_serialization(cqrs_id=master_models.Author.CQRS_ID):
            assert cqrs_state.bulk_relate_cm
            raise ValueError
    except ValueError:
        pass

    assert cqrs_state.bulk_relate_cm is None


@pytest.mark.django_db(transaction=True)
def test_bulk_relate_cqrs_serialization_register():
    author1 = master_models.Author(id=1)
    author2 = master_models.Author(id=2)

    with bulk_relate_cqrs_serialization(cqrs_id=master_models.Author.CQRS_ID):
        bulk_relate_cm = cqrs_state.bulk_relate_cm
        bulk_relate_cm.register(ValueError)
        bulk_relate_cm.register(master_models.FilteredSimplestModel())
        bulk_relate_cm.register(author1, 'default')
        bulk_relate_cm.register(author1, 'default')
        bulk_relate_cm.register(author1, 'other')
        bulk_relate_cm.register(author2, 'other')
        bulk_relate_cm.register(author2)

        assert bulk_relate_cm._mapping == {
            master_models.Author.CQRS_ID: {
                'default': {1},
                'other': {1, 2},
                None: {2},
            },
        }

    assert cqrs_state.bulk_relate_cm is None


@pytest.mark.django_db(transaction=True)
def test_bulk_relate_cqrs_serialization_get_cached_instance(mocker, django_assert_num_queries):
    produce_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    simple = master_models.SimplestModel.objects.create(id=1)

    with bulk_relate_cqrs_serialization():
        bulk_relate_cm = cqrs_state.bulk_relate_cm

        with transaction.atomic():
            author1 = master_models.Author.objects.create(id=1)
            author1.name = 'new'
            author1.save()
            author2 = master_models.Author.objects.create(id=2)

            af = master_models.AutoFieldsModel.objects.using('default').create()
            publisher = master_models.Publisher.objects.create(id=3)

        assert produce_mock.call_count == 4
        assert bulk_relate_cm._cache == {
            master_models.Author.CQRS_ID: {
                'default': {
                    1: author1,
                    2: author2,
                },
            },
        }

        assert bulk_relate_cm.get_cached_instance(publisher) is None
        assert bulk_relate_cm.get_cached_instance(ValueError, 'test') is None

        with django_assert_num_queries(0):
            assert bulk_relate_cm.get_cached_instance(simple) is None
            assert bulk_relate_cm.get_cached_instance(author1, 'default') == author1
            assert bulk_relate_cm.get_cached_instance(author1, 'default') == author1
            assert bulk_relate_cm.get_cached_instance(author1, 'other') is None
            assert bulk_relate_cm.get_cached_instance(author2, 'default') == author2
            assert bulk_relate_cm.get_cached_instance(author2) is None
            assert bulk_relate_cm.get_cached_instance(master_models.Author(id=3)) is None
            assert bulk_relate_cm.get_cached_instance(af) is None

    assert cqrs_state.bulk_relate_cm is None
