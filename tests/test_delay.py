#  Copyright © 2023 Ingram Micro Inc. All rights reserved.

from datetime import datetime, timedelta, timezone
from queue import Full

import pytest

from dj_cqrs.delay import DelayMessage, DelayQueue


def test_delay_message(mocker):
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    eta = fake_now + timedelta(seconds=10)
    mocker.patch('django.utils.timezone.now', return_value=fake_now)

    delay_message = DelayMessage(1, {'test': 'data'}, eta)

    assert delay_message.delivery_tag == 1
    assert delay_message.payload == {'test': 'data'}

    expected_eta = datetime(2020, 1, 1, second=10, tzinfo=timezone.utc)
    assert delay_message.eta == expected_eta


def test_delay_queue_put():
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    delay_message = DelayMessage(1, {'test': 'data'}, fake_now)

    delay_queue = DelayQueue()
    delay_queue.put(delay_message)

    assert delay_queue.qsize() == 1

    result_message = delay_queue.get()
    assert result_message is delay_message


def test_delay_queue_put_same_eta():
    eta = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    delay_messages = [DelayMessage(delivery_tag, None, eta) for delivery_tag in range(10)]

    delay_queue = DelayQueue()
    for delay_message in delay_messages:
        delay_queue.put(delay_message)

    assert delay_queue.qsize() == 10
    assert delay_queue.get()


def test_delay_queue_put_full():
    eta = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    delay_queue = DelayQueue(max_size=1)

    delay_queue.put(
        DelayMessage(1, None, eta),
    )
    with pytest.raises(Full):
        delay_queue.put(
            DelayMessage(2, None, eta),
        )

    assert delay_queue.qsize() == 1
    assert delay_queue.get().delivery_tag == 1


def test_delay_queue_get_ready(mocker):
    fake_put_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('django.utils.timezone.now', return_value=fake_put_now)

    delay_queue = DelayQueue()
    delay_messages = []
    for delay in (1, 0, 3600, 2):
        eta = fake_put_now + timedelta(seconds=delay)
        delay_message = DelayMessage(None, None, eta)
        delay_queue.put(delay_message)
        delay_messages.append(delay_message)
    mocker.stopall()

    fake_get_ready_now = datetime(2020, 1, 1, second=3, tzinfo=timezone.utc)
    mocker.patch('django.utils.timezone.now', return_value=fake_get_ready_now)

    ready_messages = list(delay_queue.get_ready())

    assert len(ready_messages) == 3

    sorted_expected = sorted(delay_messages, key=lambda x: x.eta)
    expected_not_ready = sorted_expected.pop()
    for expected, result in zip(sorted_expected, ready_messages):
        assert expected is result

    assert delay_queue.qsize() == 1
    result_message = delay_queue.get()
    assert result_message is expected_not_ready


def test_delay_queue_invalid_max_size():
    with pytest.raises(AssertionError) as e:
        DelayQueue(max_size=0)

    assert e.value.args[0] == 'Delay queue max_size should be positive integer.'
