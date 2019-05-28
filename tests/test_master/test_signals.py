from __future__ import unicode_literals

import pytest
from django.db.models.signals import post_save

from tests.dj.transport import publish_signal
from tests.dj_master import models


@pytest.mark.parametrize('model', (models.AllFieldsModel, models.BasicFieldsModel))
def test_signals_are_registered(model):
    assert post_save.has_listeners(model)


@pytest.mark.django_db
def test_post_save_create():
    def assert_handler(sender, **kwargs):
        payload = kwargs['payload']
        assert payload == {
            'cqrs_id': models.SimplestModel.CQRS_ID,
            'signal': 'post_save',
            'instance': {'id': 1, 'name': None},
        }

    publish_signal.connect(assert_handler)
    models.SimplestModel.objects.create(id=1)


@pytest.mark.django_db
def test_post_save_update():
    m = models.SimplestModel.objects.create(id=1)

    def assert_handler(sender, **kwargs):
        payload = kwargs['payload']
        assert payload == {
            'cqrs_id': models.SimplestModel.CQRS_ID,
            'signal': 'post_save',
            'instance': {'id': 1, 'name': 'new'},
        }

    publish_signal.connect(assert_handler)
    m.name = 'new'
    m.save(update_fields=['name'])


@pytest.mark.django_db
def test_post_save_delete():
    m = models.SimplestModel.objects.create(id=1)

    def assert_handler(sender, **kwargs):
        payload = kwargs['payload']
        assert payload == {
            'cqrs_id': models.SimplestModel.CQRS_ID,
            'signal': 'post_delete',
            'instance': {'id': 1},
        }

    publish_signal.connect(assert_handler)
    m.delete()
