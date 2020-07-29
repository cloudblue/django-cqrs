#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

from dj_cqrs.controller.consumer import consume
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
    }


def test_consumer(mocker):
    factory_mock = mocker.patch('dj_cqrs.controller.consumer.route_signal_to_replica_model')
    consume(TransportPayload('a', 'b', {}, 'c', previous_data={'e': 'f'}))

    factory_mock.assert_called_once_with('a', 'b', {}, previous_data={'e': 'f'})
