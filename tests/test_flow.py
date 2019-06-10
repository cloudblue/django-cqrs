from __future__ import unicode_literals

import pytest

from dj_master import models as master_models
from dj_replica import models as replica_models


@pytest.mark.django_db(transaction=True)
def test_create():
    master_model = master_models.BasicFieldsModel.objects.create(
        int_field=1,
        char_field='text',
    )
    assert replica_models.BasicFieldsModelRef.objects.count() == 1

    replica_model = replica_models.BasicFieldsModelRef.objects.first()
    for field_name in ('cqrs_revision', 'cqrs_updated', 'int_field', 'char_field'):
        assert getattr(master_model, field_name) == getattr(replica_model, field_name)


@pytest.mark.django_db(transaction=True)
def test_update():
    master_model = master_models.BasicFieldsModel.objects.create(
        int_field=1,
        char_field='text',
    )
    assert replica_models.BasicFieldsModelRef.objects.count() == 1

    master_model.char_field = 'new_text'
    master_model.save()
    master_model.refresh_from_db()

    assert replica_models.BasicFieldsModelRef.objects.count() == 1

    replica_model = replica_models.BasicFieldsModelRef.objects.first()
    for field_name in ('cqrs_revision', 'cqrs_updated', 'int_field', 'char_field'):
        assert getattr(master_model, field_name) == getattr(replica_model, field_name)


@pytest.mark.django_db(transaction=True)
def test_delete():
    master_model = master_models.BasicFieldsModel.objects.create(
        int_field=1,
        char_field='text',
    )
    assert replica_models.BasicFieldsModelRef.objects.count() == 1

    master_model.delete()
    assert replica_models.BasicFieldsModelRef.objects.count() == 0
