from __future__ import unicode_literals

import logging
from importlib import import_module

import pytest
from pika.exceptions import AMQPError
from six.moves import reload_module

from dj_cqrs.constants import SignalType
from dj_cqrs.dataclasses import TransportPayload
from dj_cqrs.transport.rabbit_mq import RabbitMQTransport


def test_rabbit_default_settings():
    s = RabbitMQTransport._get_settings()
    assert s[0] == 'localhost'
    assert s[1] == 5672
    assert s[2].username == 'guest' and s[2].password == 'guest'
    assert s[3] == 'cqrs'


def test_rabbit_non_default_settings(settings):
    settings.CQRS = {
        'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
        'host': 'rabbit',
        'port': 8000,
        'user': 'usr',
        'password': 'pswd',
        'exchange': 'exchange',
    }

    s = RabbitMQTransport._get_settings()
    assert s[0] == 'rabbit'
    assert s[1] == 8000
    assert s[2].username == 'usr' and s[2].password == 'pswd'
    assert s[3] == 'exchange'


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


def test_rabbit_transport_produce_connection_error(rabbit_transport, mocker, caplog):
    mocker.patch.object(RabbitMQTransport, '_get_producer_rmq_objects', side_effect=amqp_error)

    rabbit_transport.produce(TransportPayload(SignalType.SAVE, 'CQRS_ID', {'id': 1}, 1))
    assert "CQRS couldn't be published: pk = 1 (CQRS_ID)." in caplog.text


def test_rabbit_transport_produce_publish_error(rabbit_transport, mocker, caplog):
    mocker.patch.object(
        RabbitMQTransport, '_get_producer_rmq_objects', return_value=(mocker.MagicMock(), None),
    )
    mocker.patch.object(RabbitMQTransport, '_publish_message', side_effect=amqp_error)

    rabbit_transport.produce(TransportPayload(SignalType.SAVE, 'CQRS_ID', {'id': 1}, 1))
    assert "CQRS couldn't be published: pk = 1 (CQRS_ID)." in caplog.text


def test_rabbit_transport_produce_ok(rabbit_transport, mocker, caplog):
    caplog.set_level(logging.INFO)
    mocker.patch.object(
        RabbitMQTransport, '_get_producer_rmq_objects', return_value=(mocker.MagicMock(), None),
    )
    mocker.patch.object(RabbitMQTransport, '_publish_message', return_value=True)

    rabbit_transport.produce(TransportPayload(SignalType.SAVE, 'CQRS_ID', {'id': 1}, 1))
    assert 'CQRS is published: pk = 1 (CQRS_ID).' in caplog.text
