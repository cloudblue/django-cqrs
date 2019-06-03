from __future__ import unicode_literals

import pytest

from django.db.models import CharField, IntegerField

from dj_cqrs.mixins import _ReplicaMeta
from dj_cqrs.registries import ReplicaRegistry
from tests.dj_replica import models


@pytest.mark.parametrize('model', (models.BasicFieldsModelRef, models.BadTypeModelRef))
def test_models_are_registered(model):
    assert ReplicaRegistry.models[model.CQRS_ID] == model


def test_cqrs_fields_non_existing_field(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_MAPPING = {
                'chr_field': 'char_field',
                'integer_field': 'int_field',
            }

            char_field = CharField(max_length=100, primary_key=True)
            int_field = IntegerField()

            _meta = mocker.MagicMock(concrete_fields=(char_field, int_field), private_fields=())
            _meta.pk.name = 'char_field'

        _ReplicaMeta._check_cqrs_mapping(Cls)

    assert str(e.value) == 'CQRS_MAPPING field is not setup correctly for model Cls.'


def test_cqrs_fields_id_is_not_included(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_MAPPING = {
                'integer_field': 'int_field',
            }

            char_field = CharField(max_length=100, primary_key=True)
            int_field = IntegerField()

            _meta = mocker.MagicMock(concrete_fields=(char_field, int_field), private_fields=())
            _meta.pk.name = 'char_field'

        _ReplicaMeta._check_cqrs_mapping(Cls)

    assert str(e.value) == 'PK is not in CQRS_MAPPING for model Cls.'


def test_cqrs_fields_duplicates(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_MAPPING = {
                'integer_field': 'char_field',
                'char_field': 'char_field',
            }

            char_field = CharField(max_length=100, primary_key=True)
            int_field = IntegerField()

            _meta = mocker.MagicMock(concrete_fields=(char_field, int_field), private_fields=())
            _meta.pk.name = 'char_field'

        _ReplicaMeta._check_cqrs_mapping(Cls)

    assert str(e.value) == 'Duplicate names in CQRS_MAPPING field for model Cls.'
