from __future__ import unicode_literals

from dj_cqrs.controller.consumer import consume
from dj_cqrs.controller.producer import produce
from dj_cqrs.dataclasses import TransportPayload


def test_producer(mocker):
    transport_mock = mocker.patch('tests.dj.transport.TransportStub.produce')
    produce('a', 'b', {})

    assert transport_mock.call_count == 1
    assert transport_mock.call_args[0][0].to_dict() == {
        'signal_type': 'a',
        'cqrs_id': 'b',
        'instance_data': {},
    }


def test_consumer(mocker):
    factory_mock = mocker.patch('dj_cqrs.factories.ReplicaFactory.factory')
    consume(TransportPayload('a', 'b', {}))

    factory_mock.assert_called_once_with('a', 'b', {})
