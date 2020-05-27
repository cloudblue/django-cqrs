#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

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
def test_post_save_update(mocker):
    m = models.SimplestModel.objects.create(id=1)

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    m.name = 'new'
    m.save(update_fields=['name'])

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
def test_post_bulk_create(mocker):
    models.AutoFieldsModel.objects.bulk_create([models.AutoFieldsModel() for _ in range(3)])
    created_models = list(models.AutoFieldsModel.objects.all())

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    models.AutoFieldsModel.call_post_bulk_create(created_models)

    assert publisher_mock.call_count == 3


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
