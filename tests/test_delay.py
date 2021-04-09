#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from datetime import datetime, timezone

from dj_cqrs.delay import DelayMessage, DelayQueue


def test_delay_message(mocker):
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('dj_cqrs.delay.utc_now', return_value=fake_now)

    delay_message = DelayMessage(1, {'test': 'data'}, delay=10)

    assert delay_message.delivery_tag == 1
    assert delay_message.payload == {'test': 'data'}

    expected_eta = datetime(2020, 1, 1, second=10, tzinfo=timezone.utc)
    assert delay_message.eta == expected_eta


def test_delay_queue_put():
    delay_message = DelayMessage(1, {'test': 'data'}, delay=0)
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    delay_message.eta = fake_now

    delay_queue = DelayQueue()
    delay_queue.put(delay_message)

    assert delay_queue.qsize() == 1

    result_message = delay_queue.get()
    assert result_message is delay_message


def test_delay_queue_get_ready(mocker):
    fake_put_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('dj_cqrs.delay.utc_now', return_value=fake_put_now)

    delay_queue = DelayQueue()
    delay_messages = [DelayMessage(None, None, delay) for delay in (1, 0, 3600, 2)]
    for delay_message in delay_messages:
        delay_queue.put(delay_message)
    mocker.stopall()

    fake_get_ready_now = datetime(2020, 1, 1, second=3, tzinfo=timezone.utc)
    mocker.patch('dj_cqrs.delay.utc_now', return_value=fake_get_ready_now)

    ready_messages = list(delay_queue.get_ready())

    assert len(ready_messages) == 3

    sorted_expected = sorted(delay_messages, key=lambda x: x.eta)
    expected_not_ready = sorted_expected.pop()
    for expected, result in zip(sorted_expected, ready_messages):
        assert expected is result

    assert delay_queue.qsize() == 1
    result_message = delay_queue.get()
    assert result_message is expected_not_ready
