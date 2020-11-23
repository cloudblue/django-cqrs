#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import logging
import ujson
from importlib import import_module, reload

import pytest
from kombu.exceptions import KombuError

from dj_cqrs.constants import SignalType
from dj_cqrs.dataclasses import TransportPayload
from dj_cqrs.registries import ReplicaRegistry
from dj_cqrs.transport.kombu import _KombuConsumer, KombuTransport


class PublicKombuTransport(KombuTransport):
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

    @classmethod
    def create_exchange(cls, *args):
        return cls._create_exchange(*args)


def test_default_settings(settings):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.kombu.KombuTransport',
    }
    s = PublicKombuTransport.get_common_settings()
    assert s[0] == 'amqp://localhost'
    assert s[1] == 'cqrs'


def test_non_default_settings(settings, caplog):
    settings.CQRS = {
        'url': 'redis://localhost:6379',
        'exchange': 'exchange',
    }

    s = PublicKombuTransport.get_common_settings()
    assert s[0] == 'redis://localhost:6379'
    assert s[1] == 'exchange'


def test_consumer_default_settings():
    s = PublicKombuTransport.get_consumer_settings()
    assert s[1] == 10


def test_consumer_non_default_settings(settings):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.kombu.KombuTransport',
        'queue': 'q',
        'consumer_prefetch_count': 2,
    }

    s = PublicKombuTransport.get_consumer_settings()
    assert s[0] == 'q'
    assert s[1] == 2


@pytest.fixture
def kombu_transport(settings):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.kombu.KombuTransport',
        'queue': 'replica',
    }
    module = reload(import_module('dj_cqrs.transport'))
    yield module.current_transport


def kombu_error(*args, **kwargs):
    raise KombuError()


def test_produce_connection_error(kombu_transport, mocker, caplog):
    mocker.patch.object(KombuTransport, '_get_producer_kombu_objects', side_effect=kombu_error)

    kombu_transport.produce(
        TransportPayload(
            SignalType.SAVE, 'CQRS_ID', {'id': 1}, 1,
        ),
    )
    assert "CQRS couldn't be published: pk = 1 (CQRS_ID)." in caplog.text


def test_produce_publish_error(kombu_transport, mocker, caplog):
    mocker.patch.object(
        KombuTransport, '_get_producer_kombu_objects', return_value=(mocker.MagicMock(), None),
    )
    mocker.patch.object(KombuTransport, '_produce_message', side_effect=kombu_error)

    kombu_transport.produce(
        TransportPayload(
            SignalType.SAVE, 'CQRS_ID', {'id': 1}, 1,
        ),
    )
    assert "CQRS couldn't be published: pk = 1 (CQRS_ID)." in caplog.text


def test_produce_ok(kombu_transport, mocker, caplog):
    caplog.set_level(logging.INFO)
    mocker.patch.object(
        KombuTransport, '_get_producer_kombu_objects', return_value=(mocker.MagicMock(), None),
    )
    mocker.patch.object(KombuTransport, '_produce_message', return_value=True)

    kombu_transport.produce(
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
    exchange = PublicKombuTransport.create_exchange('exchange')

    PublicKombuTransport.produce_message(channel, exchange, payload)
    assert channel.basic_publish.call_count == 1

    prepare_message_args = channel.prepare_message.call_args[0]
    basic_publish_kwargs = channel.basic_publish.call_args[1]

    assert ujson.loads(prepare_message_args[0]) == \
        {
            'signal_type': SignalType.SAVE,
            'cqrs_id': 'cqrs_id',
            'instance_data': {},
            'instance_pk': 'id',
            'previous_data': {'e': 'f'},
        }

    assert prepare_message_args[2] == 'text/plain'
    assert prepare_message_args[5]['delivery_mode'] == 2

    assert basic_publish_kwargs['exchange'] == 'exchange'
    assert basic_publish_kwargs['mandatory']
    assert basic_publish_kwargs['routing_key'] == 'cqrs_id'


def test_produce_sync_message_no_queue(mocker):
    channel = mocker.MagicMock()
    payload = TransportPayload(SignalType.SYNC, 'cqrs_id', {}, None)

    exchange = PublicKombuTransport.create_exchange('exchange')

    PublicKombuTransport.produce_message(channel, exchange, payload)

    prepare_message_args = channel.prepare_message.call_args[0]
    basic_publish_kwargs = channel.basic_publish.call_args[1]

    assert ujson.loads(prepare_message_args[0]) == \
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

    exchange = PublicKombuTransport.create_exchange('exchange')

    PublicKombuTransport.produce_message(channel, exchange, payload)

    prepare_message_args = channel.prepare_message.call_args[0]
    basic_publish_kwargs = channel.basic_publish.call_args[1]
    assert ujson.loads(prepare_message_args[0]) == \
        {
            'signal_type': SignalType.SYNC,
            'cqrs_id': 'cqrs_id',
            'instance_data': {},
            'instance_pk': 'id',
            'previous_data': None,
        }
    assert basic_publish_kwargs['routing_key'] == 'cqrs.queue.cqrs_id'


def test_consume_message_ack(mocker, caplog):
    caplog.set_level(logging.INFO)
    consumer_mock = mocker.patch('dj_cqrs.controller.consumer.consume')
    message_mock = mocker.MagicMock()

    PublicKombuTransport.consume_message(
        '{"signal_type":"signal","cqrs_id":"cqrs_id","instance_data":{},'
        '"instance_pk":1, "previous_data":{}}',
        message_mock,
    )

    assert consumer_mock.call_count == 1
    assert message_mock.ack.call_count == 1

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

    PublicKombuTransport.consume_message(
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

    assert 'CQRS deprecated package structure.' in caplog.text
    assert 'CQRS is received: pk = None (cqrs_id).' not in caplog.text
    assert 'CQRS is applied: pk = None (cqrs_id).' not in caplog.text


def test_consume_message_nack(mocker, caplog):
    caplog.set_level(logging.INFO)
    mocker.patch('dj_cqrs.controller.consumer.consume', return_value=None)
    message_mock = mocker.MagicMock()
    PublicKombuTransport.consume_message(
        '{"signal_type":"signal","cqrs_id":"cqrs_id","instance_data":{},'
        '"instance_pk":1,"previous_data":null}',
        message_mock,
    )

    assert message_mock.reject.call_count == 1

    assert 'CQRS is received: pk = 1 (cqrs_id).' in caplog.text
    assert 'CQRS is denied: pk = 1 (cqrs_id).' in caplog.text


def test_consume_message_nack_deprecated_structure(mocker, caplog):
    caplog.set_level(logging.INFO)
    mocker.patch('dj_cqrs.controller.consumer.consume', return_value=None)

    PublicKombuTransport.consume_message(
        '{"signal_type":"signal","cqrs_id":"cqrs_id","instance_data":{}}',
        mocker.MagicMock(),
    )

    assert 'CQRS is received: pk = 1 (cqrs_id).' not in caplog.text
    assert 'CQRS is denied: pk = 1 (cqrs_id).' not in caplog.text


def test_consume_message_json_parsing_error(mocker, caplog):
    PublicKombuTransport.consume_message(
        '{bad_payload:',
        mocker.MagicMock(),
    )

    assert ": {bad_payload:." in caplog.text


def test_consume_message_package_structure_error(mocker, caplog):
    PublicKombuTransport.consume_message(
        '{"pk":"1"}',
        mocker.MagicMock(),
    )

    assert """CQRS couldn't be parsed: {"pk":"1"}""" in caplog.text


def test_consumer_queues(mocker):
    mocker.patch('dj_cqrs.transport.kombu.Connection')

    def callback(body, message):
        pass

    c = _KombuConsumer('amqp://localhost', 'cqrs', 'cqrs_queue', 2, callback)

    assert len(c.queues) == len(ReplicaRegistry.models) * 2


def test_consumer_consumers(mocker):
    mocker.patch('dj_cqrs.transport.kombu.Connection')

    def callback(body, message):
        pass

    c = _KombuConsumer('amqp://localhost', 'cqrs', 'cqrs_queue', 2, callback)

    consumers = c.get_consumers(mocker.MagicMock, None)
    assert len(consumers) == 1
    consumer = consumers[0]
    assert consumer.queues == c.queues
    assert consumer.callbacks[0] == callback
    assert consumer.prefetch_count == 2


def test_consumer_run(mocker):
    mocker.patch('dj_cqrs.transport.kombu.Connection')
    mocked_run = mocker.patch.object(_KombuConsumer, 'run')

    PublicKombuTransport.consume()

    mocked_run.assert_called_once()
