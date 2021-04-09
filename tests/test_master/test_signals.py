#  Copyright © 2021 Ingram Micro Inc. All rights reserved.
from datetime import datetime, timezone

import pytest
from django.db.models.signals import post_delete, post_save

from dj_cqrs.signals import post_bulk_create, post_update
from dj_cqrs.constants import SignalType
from tests.dj_master import models
from tests.utils import assert_publisher_once_called_with_args


@pytest.mark.parametrize('model', (models.AllFieldsModel, models.BasicFieldsModel))
@pytest.mark.parametrize('signal', (post_delete, post_save, post_bulk_create, post_update))
def test_signals_are_registered(model, signal):
    assert signal.has_listeners(model)


@pytest.mark.django_db(transaction=True)
def test_post_save_create(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    models.SimplestModel.objects.create(id=1)

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE, models.SimplestModel.CQRS_ID, {'id': 1, 'name': None}, 1,
    )


@pytest.mark.django_db(transaction=True)
def test_post_save_create_with_retry_fields(settings, mocker):
    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('dj_cqrs.utils.utc_now', return_value=fake_now)

    settings.CQRS['message_ttl'] = 10
    expected_expires = datetime(2020, 1, 1, second=10, tzinfo=timezone.utc)

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    models.SimplestModel.objects.create(id=1)

    assert publisher_mock.call_count == 1

    call_t_payload = publisher_mock.call_args[0][0]
    assert call_t_payload.expires == expected_expires
    assert call_t_payload.retries == 0


@pytest.mark.django_db(transaction=True)
def test_post_save_update(mocker):
    m = models.SimplestModel.objects.create(id=1)

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    m.name = 'new'
    m.save()

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE, models.SimplestModel.CQRS_ID, {'id': 1, 'name': 'new'}, 1,
    )


@pytest.mark.django_db(transaction=True)
def test_post_save_delete(mocker):
    m = models.SimplestModel.objects.create(id=1)

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    m.delete()

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.DELETE, models.SimplestModel.CQRS_ID, {'id': 1, 'cqrs_revision': 1}, 1,
    )

    cqrs_updated = publisher_mock.call_args[0][0].to_dict()['instance_data']['cqrs_updated']
    assert isinstance(cqrs_updated, str)


@pytest.mark.django_db(transaction=True)
def test_post_save_delete_with_retry_fields(settings, mocker):
    m = models.SimplestModel.objects.create(id=1)

    fake_now = datetime(2020, 1, 1, second=0, tzinfo=timezone.utc)
    mocker.patch('dj_cqrs.utils.utc_now', return_value=fake_now)

    settings.CQRS['message_ttl'] = 10
    expected_expires = datetime(2020, 1, 1, second=10, tzinfo=timezone.utc)

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    m.delete()

    assert publisher_mock.call_count == 1

    call_t_payload = publisher_mock.call_args[0][0]
    assert call_t_payload.expires == expected_expires
    assert call_t_payload.retries == 0


@pytest.mark.django_db(transaction=True)
def test_manual_post_bulk_create(mocker):
    models.AutoFieldsModel.objects.bulk_create([models.AutoFieldsModel() for _ in range(3)])
    created_models = list(models.AutoFieldsModel.objects.all())

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    models.AutoFieldsModel.call_post_bulk_create(created_models)

    assert publisher_mock.call_count == 3


@pytest.mark.django_db(transaction=True)
def test_automatic_post_bulk_create(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    instances = models.SimplestTrackedModel.cqrs.bulk_create([
        models.SimplestTrackedModel(id=i, status='new') for i in range(1, 4)
    ])

    assert len(instances) == 3
    for index in range(3):
        instance = instances[index]
        assert instance.id == index + 1
        assert instance.status == 'new'
        assert instance.cqrs_revision == 0

    assert publisher_mock.call_count == 3

    for index, call in enumerate(publisher_mock.call_args_list, start=1):
        payload = call[0][0]
        assert payload.signal_type == SignalType.SAVE
        assert payload.instance_data['id'] == index
        assert payload.instance_data['status'] == 'new'
        assert payload.instance_data['description'] is None
        assert payload.previous_data == {'status': None}


@pytest.mark.django_db(transaction=True)
def test_post_bulk_update(mocker):
    for i in range(3):
        models.SimplestModel.objects.create(id=i)
    cqrs_updated = models.SimplestModel.objects.get(id=1).cqrs_updated

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    models.SimplestModel.cqrs.bulk_update(
        queryset=models.SimplestModel.objects.filter(id__in={1}),
        name='new',
    )

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE, models.SimplestModel.CQRS_ID, {'id': 1, 'name': 'new'}, 1,
    )

    m = models.SimplestModel.objects.get(id=1)
    assert m.cqrs_updated > cqrs_updated
    assert m.cqrs_revision == 1
