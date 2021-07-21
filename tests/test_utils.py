#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from datetime import datetime, timedelta, timezone

from dj_cqrs.utils import get_expires_datetime


def test_get_expires_datetime(mocker, settings):
    settings.CQRS['master']['CQRS_MESSAGE_TTL'] = 3600
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('django.utils.timezone.now', return_value=fake_now)

    result = get_expires_datetime()

    expected_result = fake_now + timedelta(seconds=3600)
    assert result == expected_result


def test_get_expires_datetime_infinite(mocker, settings):
    settings.CQRS['master']['CQRS_MESSAGE_TTL'] = None
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('django.utils.timezone.now', return_value=fake_now)

    result = get_expires_datetime()

    assert result is None
