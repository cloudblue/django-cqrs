#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import logging
import ujson
from importlib import import_module

import pytest
from django.db import DatabaseError
from pika.exceptions import AMQPError
from six.moves import reload_module

from dj_cqrs.constants import SignalType
from dj_cqrs.dataclasses import TransportPayload
from dj_cqrs.transport.rabbit_mq import RabbitMQTransport
from tests.utils import db_error


class PublicRabbitMQTransport(RabbitMQTransport):
    @classmethod
    def get_common_settings(cls):
        return cls._get_common_settings()

    @classmethod
    def get_consumer_settings(cls):
        return cls._get_consumer_settings()

    @classmethod
    def consume_message(cls, *args):
        return cls._consume_message(*args)

    @classmethod
    def produce_message(cls, *args):
        return cls._produce_message(*args)


def test_default_settings():
    s = PublicRabbitMQTransport.get_common_settings()
    assert s[0] == 'localhost'
    assert s[1] == 5672
    assert s[2].username == 'guest' and s[2].password == 'guest'
    assert s[3] == 'cqrs'


def test_non_default_settings(settings):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
        'host': 'rabbit',
        'port': 8000,
        'user': 'usr',
        'password': 'pswd',
        'exchange': 'exchange',
    }

    s = PublicRabbitMQTransport.get_common_settings()
    assert s[0] == 'rabbit'
    assert s[1] == 8000
    assert s[2].username == 'usr' and s[2].password == 'pswd'
    assert s[3] == 'exchange'


def test_consumer_default_settings():
    s = PublicRabbitMQTransport.get_consumer_settings()
    assert s[0] is None
    assert s[1] == 10


def test_consumer_non_default_settings(settings):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
        'queue': 'q',
        'consumer_prefetch_count': 2,
    }

    s = PublicRabbitMQTransport.get_consumer_settings()
    assert s[0] == 'q'
    assert s[1] == 2


@pytest.fixture
def rabbit_transport(settings):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
        'queue': 'replica',
    }
    module = reload_module(import_module('dj_cqrs.transport'))
    yield module.current_transport


def amqp_error(*args, **kwargs):
    raise AMQPError


def test_produce_connection_error(rabbit_transport, mocker, caplog):
    mocker.patch.object(RabbitMQTransport, '_get_producer_rmq_objects', side_effect=amqp_error)

    rabbit_transport.produce(
        TransportPayload(
            SignalType.SAVE, 'CQRS_ID', {'id': 1}, 1,
        ),
    )
    assert "CQRS couldn't be published: pk = 1 (CQRS_ID)." in caplog.text


def test_produce_publish_error(rabbit_transport, mocker, caplog):
    mocker.patch.object(
        RabbitMQTransport, '_get_producer_rmq_objects', return_value=(mocker.MagicMock(), None),
    )
    mocker.patch.object(RabbitMQTransport, '_produce_message', side_effect=amqp_error)

    rabbit_transport.produce(
        TransportPayload(
            SignalType.SAVE, 'CQRS_ID', {'id': 1}, 1,
        ),
    )
    assert "CQRS couldn't be published: pk = 1 (CQRS_ID)." in caplog.text


def test_produce_ok(rabbit_transport, mocker, caplog):
    caplog.set_level(logging.INFO)
    mocker.patch.object(
        RabbitMQTransport, '_get_producer_rmq_objects', return_value=(mocker.MagicMock(), None),
    )
    mocker.patch.object(RabbitMQTransport, '_produce_message', return_value=True)

    rabbit_transport.produce(
        TransportPayload(
            SignalType.SAVE, 'CQRS_ID', {'id': 1}, 1,
        ),
    )
    assert 'CQRS is published: pk = 1 (CQRS_ID).' in caplog.text


def test_produce_message_ok(mocker):
    channel = mocker.MagicMock()
    payload = TransportPayload(
        SignalType.SAVE, 'cqrs_id', {}, 'id', previous_data={'e': 'f'},
    )

    PublicRabbitMQTransport.produce_message(channel, 'exchange', payload)

    assert channel.basic_publish.call_count == 1

    basic_publish_kwargs = channel.basic_publish.call_args[1]
    assert ujson.loads(basic_publish_kwargs['body']) == \
        {
            'signal_type': SignalType.SAVE,
            'cqrs_id': 'cqrs_id',
            'instance_data': {},
            'instance_pk': 'id',
            'previous_data': {'e': 'f'},
        }
    assert basic_publish_kwargs['exchange'] == 'exchange'
    assert basic_publish_kwargs['mandatory']
    assert basic_publish_kwargs['routing_key'] == 'cqrs_id'
    assert basic_publish_kwargs['properties'].content_type == 'text/plain'
    assert basic_publish_kwargs['properties'].delivery_mode == 2


def test_produce_sync_message_no_queue(mocker):
    channel = mocker.MagicMock()
    payload = TransportPayload(SignalType.SYNC, 'cqrs_id', {}, None)

    PublicRabbitMQTransport.produce_message(channel, 'exchange', payload)

    basic_publish_kwargs = channel.basic_publish.call_args[1]
    assert ujson.loads(basic_publish_kwargs['body']) == \
        {
            'signal_type': SignalType.SYNC,
            'cqrs_id': 'cqrs_id',
            'instance_data': {},
            'instance_pk': None,
            'previous_data': None,
        }
    assert basic_publish_kwargs['routing_key'] == 'cqrs_id'


def test_produce_sync_message_queue(mocker):
    channel = mocker.MagicMock()
    payload = TransportPayload(SignalType.SYNC, 'cqrs_id', {}, 'id', 'queue')

    PublicRabbitMQTransport.produce_message(channel, 'exchange', payload)

    basic_publish_kwargs = channel.basic_publish.call_args[1]
    assert ujson.loads(basic_publish_kwargs['body']) == \
        {
            'signal_type': SignalType.SYNC,
            'cqrs_id': 'cqrs_id',
            'instance_data': {},
            'instance_pk': 'id',
            'previous_data': None,
        }
    assert basic_publish_kwargs['routing_key'] == 'cqrs.queue.cqrs_id'


def test_consume_connection_error(rabbit_transport, mocker, caplog):
    mocker.patch.object(
        RabbitMQTransport, '_get_consumer_rmq_objects', side_effect=amqp_error,
    )
    mocker.patch('time.sleep', side_effect=db_error)

    with pytest.raises(DatabaseError):
        rabbit_transport.consume()

    assert 'AMQP connection error. Reconnecting...' in caplog.text


def test_consume_ok(rabbit_transport, mocker):
    channel_mock = mocker.MagicMock()
    channel_mock.start_consuming = db_error

    mocker.patch.object(
        RabbitMQTransport, '_get_consumer_rmq_objects', return_value=(None, channel_mock),
    )

    with pytest.raises(DatabaseError):
        rabbit_transport.consume()


def test_consume_message_ack(mocker, caplog):
    caplog.set_level(logging.INFO)
    consumer_mock = mocker.patch('dj_cqrs.controller.consumer.consume')

    PublicRabbitMQTransport.consume_message(
        mocker.MagicMock(),
        mocker.MagicMock(),
        None,
        '{"signal_type":"signal","cqrs_id":"cqrs_id","instance_data":{},'
        '"instance_pk":1, "previous_data":{}}',
    )

    assert consumer_mock.call_count == 1

    payload = consumer_mock.call_args[0][0]
    assert payload.signal_type == 'signal'
    assert payload.cqrs_id == 'cqrs_id'
    assert payload.instance_data == {}
    assert payload.previous_data == {}
    assert payload.pk == 1

    assert 'CQRS is received: pk = 1 (cqrs_id).' in caplog.text
    assert 'CQRS is applied: pk = 1 (cqrs_id).' in caplog.text


def test_consume_message_ack_deprecated_structure(mocker, caplog):
    caplog.set_level(logging.INFO)
    consumer_mock = mocker.patch('dj_cqrs.controller.consumer.consume')

    PublicRabbitMQTransport.consume_message(
        mocker.MagicMock(),
        mocker.MagicMock(),
        None,
        '{"signal_type":"signal","cqrs_id":"cqrs_id",'
        '"instance_data":{},"previous_data":null}',
    )

    assert consumer_mock.call_count == 1

    payload = consumer_mock.call_args[0][0]
    assert payload.signal_type == 'signal'
    assert payload.cqrs_id == 'cqrs_id'
    assert payload.instance_data == {}
    assert payload.pk is None

    assert 'CQRS deprecated package structure.' in caplog.text
    assert 'CQRS is received: pk = None (cqrs_id).' not in caplog.text
    assert 'CQRS is applied: pk = None (cqrs_id).' not in caplog.text


def test_consume_message_nack(mocker, caplog):
    caplog.set_level(logging.INFO)
    mocker.patch('dj_cqrs.controller.consumer.consume', return_value=None)

    PublicRabbitMQTransport.consume_message(
        mocker.MagicMock(),
        mocker.MagicMock(),
        None,
        '{"signal_type":"signal","cqrs_id":"cqrs_id","instance_data":{},'
        '"instance_pk":1,"previous_data":null}',
    )

    assert 'CQRS is received: pk = 1 (cqrs_id).' in caplog.text
    assert 'CQRS is denied: pk = 1 (cqrs_id).' in caplog.text


def test_consume_message_nack_deprecated_structure(mocker, caplog):
    caplog.set_level(logging.INFO)
    mocker.patch('dj_cqrs.controller.consumer.consume', return_value=None)

    PublicRabbitMQTransport.consume_message(
        mocker.MagicMock(),
        mocker.MagicMock(),
        None,
        '{"signal_type":"signal","cqrs_id":"cqrs_id","instance_data":{}}',
    )

    assert 'CQRS is received: pk = 1 (cqrs_id).' not in caplog.text
    assert 'CQRS is denied: pk = 1 (cqrs_id).' not in caplog.text


def test_consume_message_json_parsing_error(mocker, caplog):
    PublicRabbitMQTransport.consume_message(
        mocker.MagicMock(), mocker.MagicMock(), None, '{bad_payload:',
    )

    assert ": {bad_payload:." in caplog.text


def test_consume_message_package_structure_error(mocker, caplog):
    PublicRabbitMQTransport.consume_message(
        mocker.MagicMock(), mocker.MagicMock(), None, '{"pk":"1"}',
    )

    assert """CQRS couldn't be parsed: {"pk":"1"}""" in caplog.text
