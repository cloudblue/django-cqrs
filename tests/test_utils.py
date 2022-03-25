#  Copyright © 2022 Ingram Micro Inc. All rights reserved.

from datetime import datetime, timedelta, timezone

from dj_cqrs.utils import (
    get_delay_queue_max_size, get_message_expiration_dt, get_messages_prefetch_count_per_worker,
)


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
