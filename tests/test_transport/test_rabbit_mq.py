#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import logging
from datetime import datetime, timezone

import ujson
from importlib import import_module, reload

import pytest
from django.db import DatabaseError
from pika.exceptions import AMQPError

from dj_cqrs.delay import DelayQueue, DelayMessage
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
    def fail_message(cls, *args):
        return cls._fail_message(*args)

    @classmethod
    def process_delay_messages(cls, *args):
        return cls._process_delay_messages(*args)

    @classmethod
    def produce_message(cls, *args):
        return cls._produce_message(*args)


def test_default_settings():
    s = PublicRabbitMQTransport.get_common_settings()
    assert s[0] == 'localhost'
    assert s[1] == 5672
    assert s[2].username == 'guest' and s[2].password == 'guest'
    assert s[3] == 'cqrs'


def test_non_default_settings(settings, caplog):
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


def test_default_url_settings(settings):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
        'url': 'amqp://localhost'
    }
    s = PublicRabbitMQTransport.get_common_settings()
    assert s[0] == 'localhost'
    assert s[1] == 5672
    assert s[2].username == 'guest' and s[2].password == 'guest'
    assert s[3] == 'cqrs'


def test_non_default_url_settings(settings):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
        'url': 'amqp://usr:pswd@rabbit:8000',
        'exchange': 'exchange',
    }
    s = PublicRabbitMQTransport.get_common_settings()
    assert s[0] == 'rabbit'
    assert s[1] == 8000
    assert s[2].username == 'usr' and s[2].password == 'pswd'
    assert s[3] == 'exchange'


def test_invalid_url_settings(settings):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
        'url': 'rabbit://localhost'
    }
    with pytest.raises(AssertionError) as ei:
        PublicRabbitMQTransport.get_common_settings()

    assert ei.match('Scheme must be "amqp" for RabbitMQTransport.')


def test_consumer_non_default_settings(settings, caplog):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
        'queue': 'q',
        'consumer_prefetch_count': 2,
    }

    s = PublicRabbitMQTransport.get_consumer_settings()
    assert s[0] == 'q'
    assert "The 'consumer_prefetch_count' setting is ignored for RabbitMQTransport." in caplog.text


@pytest.fixture
def rabbit_transport(settings):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
        'queue': 'replica',
    }
    module = reload(import_module('dj_cqrs.transport'))
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
    expires = datetime(2100, 1, 1, tzinfo=timezone.utc)
    expected_expires = '2100-01-01T00:00:00+00:00'

    channel = mocker.MagicMock()
    payload = TransportPayload(
        SignalType.SAVE,
        cqrs_id='cqrs_id',
        instance_data={},
        instance_pk='id',
        previous_data={'e': 'f'},
        expires=expires,
        retries=2,
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
            'correlation_id': None,
            'expires': expected_expires,
            'retries': 2,
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
            'correlation_id': None,
            'expires': None,
            'retries': 0,
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
            'correlation_id': None,
            'expires': None,
            'retries': 0,
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
    consumer_generator = (v for v in [(1, None, None)])
    mocker.patch.object(
        RabbitMQTransport,
        '_get_consumer_rmq_objects',
        return_value=(None, None, consumer_generator),
    )
    mocker.patch.object(
        RabbitMQTransport, '_consume_message', db_error,
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
        '"instance_pk":1, "previous_data":{}, "correlation_id":"abc",'
        '"expires":"2100-01-01T00:00:00+00:00", "retries":1}',
        mocker.MagicMock(),
    )

    assert consumer_mock.call_count == 1

    payload = consumer_mock.call_args[0][0]
    assert payload.signal_type == 'signal'
    assert payload.cqrs_id == 'cqrs_id'
    assert payload.instance_data == {}
    assert payload.previous_data == {}
    assert payload.pk == 1
    assert payload.correlation_id == 'abc'
    assert payload.expires == datetime(2100, 1, 1, tzinfo=timezone.utc)
    assert payload.retries == 1

    assert 'CQRS is received: pk = 1 (cqrs_id).' in caplog.text
    assert 'CQRS is applied: pk = 1 (cqrs_id).' in caplog.text


def test_consume_message_ack_deprecated_structure(settings, mocker, caplog):
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('django.utils.timezone.now', return_value=fake_now)

    settings.CQRS['message_ttl'] = 10
    expected_expires = datetime(2020, 1, 1, second=10, tzinfo=timezone.utc)

    caplog.set_level(logging.INFO)
    consumer_mock = mocker.patch('dj_cqrs.controller.consumer.consume')

    PublicRabbitMQTransport.consume_message(
        mocker.MagicMock(),
        mocker.MagicMock(),
        None,
        '{"signal_type":"signal","cqrs_id":"cqrs_id",'
        '"instance_data":{},"previous_data":null}',
        mocker.MagicMock(),
    )

    assert consumer_mock.call_count == 1

    payload = consumer_mock.call_args[0][0]
    assert payload.signal_type == 'signal'
    assert payload.cqrs_id == 'cqrs_id'
    assert payload.instance_data == {}
    assert payload.pk is None
    assert payload.retries == 0
    assert payload.expires == expected_expires

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
        '{"signal_type":"signal","cqrs_id":"basic","instance_data":{},'
        '"instance_pk":1,"previous_data":null,'
        '"expires":"2100-01-01T00:00:00+00:00", "retries":0}',
        mocker.MagicMock(),
    )

    assert 'CQRS is received: pk = 1 (basic).' in caplog.text
    assert 'CQRS is failed: pk = 1 (basic), retries = 0.' in caplog.text


def test_consume_message_nack_deprecated_structure(mocker, caplog):
    caplog.set_level(logging.INFO)
    mocker.patch('dj_cqrs.controller.consumer.consume', return_value=None)

    PublicRabbitMQTransport.consume_message(
        mocker.MagicMock(),
        mocker.MagicMock(),
        None,
        '{"signal_type":"signal","cqrs_id":"cqrs_id","instance_data":{}}',
        mocker.MagicMock(),
    )

    assert 'CQRS is received: pk = 1 (cqrs_id).' not in caplog.text
    assert 'CQRS is denied: pk = 1 (cqrs_id).' not in caplog.text


def test_consume_message_expired(mocker, caplog):
    caplog.set_level(logging.INFO)
    channel = mocker.MagicMock()

    PublicRabbitMQTransport.consume_message(
        channel,
        mocker.MagicMock(),
        None,
        '{"signal_type":"signal","cqrs_id":"cqrs_id","instance_data":{},'
        '"instance_pk":1,"previous_data":null,'
        '"expires":"2000-01-01T00:00:00+00:00", "retries":0}',
        mocker.MagicMock(),
    )

    assert channel.basic_nack.call_count == 1
    assert 'CQRS is received: pk = 1 (cqrs_id).' in caplog.text
    assert 'CQRS is denied: pk = 1 (cqrs_id).' in caplog.text


def test_consume_message_json_parsing_error(mocker, caplog):
    PublicRabbitMQTransport.consume_message(
        mocker.MagicMock(), mocker.MagicMock(), None, '{bad_payload:', mocker.MagicMock(),
    )

    assert ": {bad_payload:." in caplog.text


def test_consume_message_package_structure_error(mocker, caplog):
    PublicRabbitMQTransport.consume_message(
        mocker.MagicMock(), mocker.MagicMock(), None, '{"pk":"1"}', mocker.MagicMock(),
    )

    assert """CQRS couldn't be parsed: {"pk":"1"}""" in caplog.text


def test_fail_message_with_retry(mocker):
    payload = TransportPayload(SignalType.SAVE, 'basic', {'id': 1}, 1)
    delay_queue = DelayQueue()

    PublicRabbitMQTransport.fail_message(mocker.MagicMock(), 100, payload, None, delay_queue)

    assert delay_queue.qsize() == 1

    delay_message = delay_queue.get()
    assert delay_message.delivery_tag == 100
    assert delay_message.payload is payload


def test_fail_message_without_retry(settings, mocker, caplog):
    settings.CQRS['max_retries'] = 1

    channel = mocker.MagicMock()
    payload = TransportPayload(SignalType.SAVE, 'basic', {'id': 1}, 1, retries=2)
    delay_queue = DelayQueue()

    PublicRabbitMQTransport.fail_message(channel, 1, payload, None, delay_queue)

    assert delay_queue.qsize() == 0
    assert channel.basic_nack.call_count == 1

    assert 'CQRS is failed: pk = 1 (basic), retries = 2.' in caplog.text
    assert 'CQRS is denied: pk = 1 (basic).' in caplog.text


def test_process_delay_messages(mocker, caplog):
    channel = mocker.MagicMock()
    produce = mocker.patch('dj_cqrs.transport.rabbit_mq.RabbitMQTransport.produce')

    payload = TransportPayload(SignalType.SAVE, 'CQRS_ID', {'id': 1}, 1)
    delay_queue = DelayQueue()
    delay_queue.put(
        DelayMessage(delivery_tag=1, payload=payload, eta=datetime.now(tz=timezone.utc))
    )

    PublicRabbitMQTransport.process_delay_messages(channel, delay_queue)

    assert delay_queue.qsize() == 0
    assert channel.basic_nack.call_count == 1
    assert produce.call_count == 1

    produce_payload = produce.call_args[0][0]
    assert produce_payload is payload
    assert produce_payload.retries == 1

    assert 'CQRS is requeued: pk = 1 (CQRS_ID)' in caplog.text
