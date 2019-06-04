from __future__ import unicode_literals

import pytest

from django.db.models import CharField, IntegerField
from django.utils.timezone import now

from dj_cqrs.mixins import _ReplicaMeta
from tests.dj_replica import models as replica_models


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


def test_create_ok():
    raise NotImplementedError


def test_create_db_error():
    raise NotImplementedError


def test_update_ok():
    raise NotImplementedError


def test_update_db_error():
    raise NotImplementedError


@pytest.mark.django_db
def test_delete_ok():
    dt = now()
    replica_models.BasicFieldsModelRef.objects.create(
        int_field=1, cqrs_counter=0, cqrs_updated=dt,
    )

    replica_models.BasicFieldsModelRef.cqrs_delete({
        'id': 1, 'cqrs_counter': 0, 'cqrs_updated': dt,
    })
    assert replica_models.BasicFieldsModelRef.objects.count() == 0


def test_delete_db_error():
    raise NotImplementedError


def test_save_bad_master_data():
    raise NotImplementedError


def test_save_no_pk_in_master_data():
    raise NotImplementedError


def test_save_no_cqrs_fields_in_master_data():
    raise NotImplementedError


def test_delete_no_id_in_master_data():
    raise NotImplementedError


def test_delete_no_cqrs_fields_in_master_data():
    raise NotImplementedError


def test_update_before_create_is_over():
    raise NotImplementedError


def test_wrong_update_order():
    raise NotImplementedError


def test_create_before_delete_is_over():
    raise NotImplementedError
