#  Copyright © 2023 Ingram Micro Inc. All rights reserved.

import pytest
from django.conf import settings
from django.utils.timezone import now

from dj_cqrs.constants import SignalType
from dj_cqrs.controller.consumer import consume, route_signal_to_replica_model
from dj_cqrs.controller.producer import produce
from dj_cqrs.dataclasses import TransportPayload
from tests.dj_replica.models import AbstractModel, OnlyDirectSyncModel


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
        'meta': None,
    }


def test_consumer(mocker):
    factory_mock = mocker.patch('dj_cqrs.controller.consumer.route_signal_to_replica_model')
    consume(TransportPayload('a', 'b', {}, 'c', previous_data={'e': 'f'}, queue='xyz'))

    factory_mock.assert_called_once_with(
        'a', 'b', {}, previous_data={'e': 'f'}, meta=None, queue='xyz',
    )


def test_changed_payload_data_during_consume(mocker):
    def change_data(*args, **kwargs):
        instance_data = args[2]
        instance_data['instance_key'] = 'changed instance'
        kwargs['previous_data']['previous_key'] = 'changed previous'

    factory_mock = mocker.patch(
        'dj_cqrs.controller.consumer.route_signal_to_replica_model',
        side_effect=change_data,
    )

    payload = TransportPayload(
        SignalType.SAVE,
        cqrs_id='b',
        instance_data={'instance_key': 'initial instance'},
        instance_pk='c',
        previous_data={'previous_key': 'initial previous'},
    )
    consume(payload)

    assert factory_mock.call_count == 1
    assert payload.instance_data == {'instance_key': 'initial instance'}
    assert payload.previous_data == {'previous_key': 'initial previous'}


@pytest.mark.django_db(transaction=True)
def test_route_signal_to_replica_model_with_db(django_assert_num_queries):
    query_counter = 0 if settings.DB_ENGINE == 'postgres' else 1
    with django_assert_num_queries(query_counter):
        route_signal_to_replica_model(SignalType.SAVE, 'lock', {})


@pytest.mark.django_db(transaction=True)
def test_route_signal_to_replica_model_integrity_error(caplog):
    instance_data = {
        'id': 10,
        'author': {
            'id': 100,
        },
        'cqrs_revision': 0,
        'cqrs_updated': now(),
    }
    instance = route_signal_to_replica_model(SignalType.SAVE, 'article', instance_data)
    assert not instance

    errors = {
        'sqlite': 'FOREIGN KEY constraint failed',
        'postgres': (
            'insert or update on table "dj_replica_article" violates foreign key constraint'
        ),
        'mysql': 'Cannot add or update a child row: a foreign key constraint',
    }

    assert errors[settings.DB_ENGINE] in caplog.text


def test_route_signal_to_replica_model_without_db():
    with pytest.raises(NotImplementedError):
        route_signal_to_replica_model(SignalType.SAVE, 'no_db', {})


@pytest.mark.parametrize('queue', ('abc', None))
def test_route_signal_to_replica_with_only_direct_syncs(queue):
    assert route_signal_to_replica_model(
        signal_type=SignalType.SYNC,
        cqrs_id=OnlyDirectSyncModel.CQRS_ID,
        instance_data={},
        queue=queue,
    ) is True


@pytest.mark.django_db
@pytest.mark.parametrize('data, pk_repr', (({}, 'None'), ({'id': '123'}, '123')))
def test_route_signal_to_replica_exception(data, pk_repr, caplog):
    assert route_signal_to_replica_model(
        signal_type=SignalType.SAVE,
        cqrs_id=AbstractModel.CQRS_ID,
        instance_data=data,
    ) is None

    assert 'pk = {pk}'.format(pk=pk_repr) in caplog.text
