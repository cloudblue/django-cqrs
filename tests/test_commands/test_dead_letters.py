#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import ujson
from datetime import datetime

import pytest
from django.utils import timezone

from dj_cqrs.constants import SignalType
from django.core.management import call_command, CommandError
from dj_cqrs.management.commands.cqrs_dead_letters import Command, RabbitMQTransport


COMMAND_NAME = 'cqrs_dead_letters'


def test_dump(capsys, mocker):
    mocker.patch.object(Command, 'check_transport')
    mocker.patch.object(
        RabbitMQTransport,
        '_get_consumer_settings',
        return_value=('queue', 'dead_letters_queue')
    )
    mocker.patch.object(
        RabbitMQTransport,
        '_get_common_settings',
        return_value=('host', 'port', mocker.MagicMock(), 'exchange')
    )

    queue = mocker.MagicMock()
    queue.method.message_count = 1
    message_body = ujson.dumps({'cqrs_id': 'test'}).encode('utf-8')

    channel = mocker.MagicMock()
    channel.consume = lambda *args, **kwargs: (v for v in [(None, None, message_body)])
    channel.queue_declare = lambda *args, **kwargs: queue
    mocker.patch.object(
        RabbitMQTransport,
        '_create_connection',
        return_value=(mocker.MagicMock(), channel)
    )
    mocker.patch.object(RabbitMQTransport, '_nack')

    call_command(COMMAND_NAME, 'dump')

    captured = capsys.readouterr()
    assert captured.out.strip() == message_body.decode('utf-8')


def test_handle_retry(settings, capsys, mocker):
    produce_channel = mocker.MagicMock()
    mocker.patch.object(
        RabbitMQTransport,
        '_get_producer_rmq_objects',
        return_value=(None, produce_channel)
    )

    channel = mocker.MagicMock()
    method_frame = mocker.MagicMock()
    method_frame.delivery_tag = 12

    settings.CQRS['master']['CQRS_MESSAGE_TTL'] = 3600
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('django.utils.timezone.now', return_value=fake_now)
    message = {
        'signal_type': SignalType.SAVE,
        'cqrs_id': 'test',
        'instance_data': {'id': 123},
        'instance_pk': 1,
        'previous_data': None,
        'correlation_id': None,
        'expires': '2020-01-01T00:00:00+00:00',
        'retries': 30,
    }
    consumer_generator = (v for v in [(method_frame, None, ujson.dumps(message))])

    command = Command()
    command.handle_retry(channel, consumer_generator, dead_letters_count=1)

    assert produce_channel.basic_publish.call_count == 1

    produce_kwargs = produce_channel.basic_publish.call_args[1]
    assert produce_kwargs['routing_key'] == 'cqrs.replica.test'

    produce_message = ujson.loads(produce_kwargs['body'])
    assert produce_message['instance_data'] == message['instance_data']
    assert produce_message['expires'] == '2020-01-01T01:00:00+00:00'
    assert produce_message['retries'] == 0

    captured = capsys.readouterr()
    total_msg, retrying_msg, body_msg = captured.out.strip().split('\n')

    assert total_msg == 'Total dead letters: 1'
    assert retrying_msg == 'Retrying: 1/1'
    assert '2020-01-01T01:00:00+00:00' in body_msg

    assert channel.basic_nack.call_count == 1
    assert channel.basic_nack.call_args[0][0] == 12


def test_handle_purge(capsys, mocker):
    channel = mocker.MagicMock()

    command = Command()
    command.handle_purge(channel, 'dead_letters_test', dead_letter_count=3)

    assert channel.queue_purge.call_count == 1
    assert channel.queue_purge.call_args[0][0] == 'dead_letters_test'

    captured = capsys.readouterr()
    total_msg, purged_msg = captured.out.strip().split('\n')

    assert total_msg == 'Total dead letters: 3'
    assert purged_msg == 'Purged'


def test_handle_purge_empty_queue(capsys, mocker):
    channel = mocker.MagicMock()

    command = Command()
    command.handle_purge(channel, 'dead_letters_test', dead_letter_count=0)

    assert channel.queue_purge.call_count == 0

    captured = capsys.readouterr()
    assert captured.out.strip() == 'Total dead letters: 0'


def test_check_transport(settings):
    command = Command()

    with pytest.raises(CommandError) as e:
        command.check_transport()

    assert "Dead letters commands available only for RabbitMQTransport." in str(e)
