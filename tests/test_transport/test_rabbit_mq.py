from __future__ import unicode_literals

import logging
from importlib import import_module

import pytest
from pika.exceptions import AMQPError
from six.moves import reload_module

from dj_cqrs.constants import SignalType
from dj_cqrs.dataclasses import TransportPayload
from dj_cqrs.transport.rabbit_mq import RabbitMQTransport


class TestRabbitMQTransport(RabbitMQTransport):
    @classmethod
    def get_common_settings(cls):
        return cls._get_common_settings()

    @classmethod
    def get_consumer_settings(cls):
        return cls._get_consumer_settings()


def test_default_settings():
    s = TestRabbitMQTransport.get_common_settings()
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

    s = TestRabbitMQTransport.get_common_settings()
    assert s[0] == 'rabbit'
    assert s[1] == 8000
    assert s[2].username == 'usr' and s[2].password == 'pswd'
    assert s[3] == 'exchange'


def test_consumer_default_settings():
    s = TestRabbitMQTransport.get_consumer_settings()
    assert s[0] is None
    assert s[1] == 10


def test_consumer_non_default_settings(settings):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
        'queue': 'q',
        'consumer_prefetch_count': 2,
    }

    s = TestRabbitMQTransport.get_consumer_settings()
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


def test_produce_message_ok(mocker, caplog):
    raise NotImplementedError


def test_consume_connection_error(rabbit_transport, mocker, caplog):
    raise NotImplementedError


def test_consume_ok(rabbit_transport, mocker, caplog):
    raise NotImplementedError


def test_consume_message_ok(mocker, caplog):
    raise NotImplementedError


def test_consume_message_parsing_error(mocker, caplog):
    raise NotImplementedError
