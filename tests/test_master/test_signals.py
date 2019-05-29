from __future__ import unicode_literals

import pytest
from django.db.models.signals import post_delete, post_save

from dj_cqrs.signals import post_bulk_create, post_update
from dj_cqrs.constants import SignalType
from tests.dj.transport import publish_signal
from tests.dj_master import models


@pytest.mark.parametrize('model', (models.AllFieldsModel, models.BasicFieldsModel))
@pytest.mark.parametrize('signal', (post_delete, post_save, post_bulk_create, post_update))
def test_signals_are_registered(model, signal):
    assert signal.has_listeners(model)


@pytest.mark.django_db
def test_post_save_create():
    def assert_handler(sender, **kwargs):
        payload = kwargs['payload']
        assert payload.to_dict() == {
            'cqrs_id': models.SimplestModel.CQRS_ID,
            'signal_type': SignalType.SAVE,
            'instance_data': {'id': 1, 'name': None},
        }

    publish_signal.connect(assert_handler)
    models.SimplestModel.objects.create(id=1)


@pytest.mark.django_db
def test_post_save_update():
    m = models.SimplestModel.objects.create(id=1)

    def assert_handler(sender, **kwargs):
        payload = kwargs['payload']
        assert payload.to_dict() == {
            'cqrs_id': models.SimplestModel.CQRS_ID,
            'signal_type': SignalType.SAVE,
            'instance_data': {'id': 1, 'name': 'new'},
        }

    publish_signal.connect(assert_handler)
    m.name = 'new'
    m.save(update_fields=['name'])


@pytest.mark.django_db
def test_post_save_delete():
    m = models.SimplestModel.objects.create(id=1)

    def assert_handler(sender, **kwargs):
        payload = kwargs['payload']
        assert payload.to_dict() == {
            'cqrs_id': models.SimplestModel.CQRS_ID,
            'signal_type': SignalType.DELETE,
            'instance_data': {'id': 1},
        }

    publish_signal.connect(assert_handler)
    m.delete()


@pytest.mark.django_db
def test_post_bulk_create():
    models.AutoFieldsModel.objects.bulk_create([models.AutoFieldsModel() for _ in range(3)])
    created_models = list(models.AutoFieldsModel.objects.all())

    def assert_bulk_create(sender, **kwargs):
        assert sender == models.AutoFieldsModel
        assert len(kwargs['instances']) == 3

    post_bulk_create.connect(assert_bulk_create)
    models.AutoFieldsModel.call_post_bulk_create(created_models)


@pytest.mark.django_db
def test_post_update():
    for i in range(3):
        models.SimplestModel.objects.create(id=i)

    def assert_update(sender, **kwargs):
        assert sender == models.SimplestModel
        assert len(kwargs['instances']) == 2

    post_update.connect(assert_update)
    models.SimplestModel.cqrs.update(
        queryset=models.SimplestModel.objects.filter(id__in={1, 2}),
        name='new',
    )
