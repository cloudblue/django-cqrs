#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import pytest

from dj_cqrs.constants import SignalType
from dj_cqrs.controller.consumer import consume, route_signal_to_replica_model
from dj_cqrs.controller.producer import produce
from dj_cqrs.dataclasses import TransportPayload


def test_producer(mocker):
    transport_mock = mocker.patch('tests.dj.transport.TransportStub.produce')
    produce(TransportPayload('a', 'b', {}, 'c', previous_data={'e': 'f'}))

    assert transport_mock.call_count == 1
    assert transport_mock.call_args[0][0].to_dict() == {
        'signal_type': 'a',
        'cqrs_id': 'b',
        'instance_data': {},
        'instance_pk': 'c',
        'previous_data': {'e': 'f'},
        'correlation_id': None,
        'expires': None,
        'retries': 0,
    }


def test_consumer(mocker):
    factory_mock = mocker.patch('dj_cqrs.controller.consumer.route_signal_to_replica_model')
    consume(TransportPayload('a', 'b', {}, 'c', previous_data={'e': 'f'}))

    factory_mock.assert_called_once_with('a', 'b', {}, previous_data={'e': 'f'})


@pytest.mark.django_db(transaction=True)
def test_route_signal_to_replica_model_with_db(django_assert_num_queries):
    with django_assert_num_queries(1):
        route_signal_to_replica_model(SignalType.SAVE, 'lock', {})


def test_route_signal_to_replica_model_without_db():
    with pytest.raises(NotImplementedError):
        route_signal_to_replica_model(SignalType.SAVE, 'no_db', {})
