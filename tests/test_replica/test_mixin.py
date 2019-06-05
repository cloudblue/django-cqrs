from __future__ import unicode_literals

import pytest

from django.db.models import CharField, IntegerField
from django.utils.timezone import now

from dj_cqrs.metas import ReplicaMeta
from tests.dj_replica import models
from tests.utils import db_error


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

        ReplicaMeta._check_cqrs_mapping(Cls)

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

        ReplicaMeta._check_cqrs_mapping(Cls)

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

        ReplicaMeta._check_cqrs_mapping(Cls)

    assert str(e.value) == 'Duplicate names in CQRS_MAPPING field for model Cls.'


@pytest.mark.django_db
def test_create_simple():
    instance = models.BasicFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_counter': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
        'bool_field': False,
        'date_field': None,
        'datetime_field': now(),
        'float_field': 1.25,
    })
    assert isinstance(instance, models.BasicFieldsModelRef)

    instance.refresh_from_db()
    assert instance.char_field == 'text'
    assert instance.float_field == 1.25


@pytest.mark.django_db
def test_create_simple_excessive_data():
    instance = models.BasicFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_counter': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
        'unexpected_field': 'value',
    })
    assert isinstance(instance, models.BasicFieldsModelRef)


def test_create_simple_insufficient_data(caplog):
    models.BasicFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_counter': 0,
        'cqrs_updated': now(),
    })

    assert 'Not all required CQRS fields are provided in data (basic).' in caplog.text


@pytest.mark.django_db
def test_create_mapped(caplog):
    instance = models.MappedFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_counter': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })
    assert isinstance(instance, models.MappedFieldsModelRef)

    instance.refresh_from_db()
    assert instance.id == 1
    assert instance.name == 'text'


@pytest.mark.django_db
def test_create_db_error(mocker, caplog):
    mocker.patch.object(models.BasicFieldsModelRef.objects, 'create', side_effect=db_error)

    models.BasicFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_counter': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })
    assert 'CQRS create error: pk = 1 (basic).' in caplog.text


def test_update_ok():
    raise NotImplementedError


def test_update_non_existing_id():
    raise NotImplementedError


def test_update_db_error():
    raise NotImplementedError


@pytest.mark.django_db
def test_delete_ok():
    dt = now()
    models.BasicFieldsModelRef.objects.create(
        int_field=1,
        cqrs_counter=0,
        cqrs_updated=dt,
    )

    is_deleted = models.BasicFieldsModelRef.cqrs_delete({
        'id': 1,
        'cqrs_counter': 0,
        'cqrs_updated': dt,
    })

    assert is_deleted
    assert models.BasicFieldsModelRef.objects.count() == 0


@pytest.mark.django_db
def test_delete_non_existing_id():
    is_deleted = models.BasicFieldsModelRef.cqrs_delete({
        'id': 1,
        'cqrs_counter': 0,
        'cqrs_updated': now(),
    })

    assert is_deleted
    assert models.BasicFieldsModelRef.objects.count() == 0


def test_delete_db_error(mocker, caplog):
    mocker.patch.object(models.BasicFieldsModelRef.objects, 'filter', side_effect=db_error)

    is_deleted = models.BasicFieldsModelRef.cqrs_delete({
        'id': 1,
        'cqrs_counter': 0,
        'cqrs_updated': now(),
    })

    assert not is_deleted
    assert 'CQRS delete error: pk = 1' in caplog.text


@pytest.mark.django_db
def test_save_bad_master_data_field_type(caplog):
    models.BadTypeModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_counter': 0,
        'cqrs_updated': now(),
        'datetime_field': now(),
    })
    assert 'CQRS create error: pk = 1 (basic_1).' in caplog.text


def test_save_no_pk_in_master_data(caplog):
    models.BasicFieldsModelRef.cqrs_save({
        'id': 1,
        'cqrs_counter': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })

    assert 'CQRS PK is not provided in data (basic).' in caplog.text


def test_save_no_cqrs_fields_in_master_data(caplog):
    models.BasicFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_counter': 0,
        'char_field': 'text',
    })

    assert 'CQRS sync fields are not provided in data (basic).' in caplog.text


def test_delete_no_id_in_master_data(caplog):
    is_deleted = models.BasicFieldsModelRef.cqrs_delete({
        'cqrs_counter': 0,
        'cqrs_updated': now(),
    })

    assert not is_deleted
    assert 'CQRS PK is not provided in data (basic).' in caplog.text


def test_delete_no_cqrs_fields_in_master_data(caplog):
    is_deleted = models.BasicFieldsModelRef.cqrs_delete({
        'id': 1,
        'cqrs_counter': 0,
    })

    assert not is_deleted
    assert 'CQRS sync fields are not provided in data (basic).' in caplog.text


def test_update_before_create_is_over():
    raise NotImplementedError


def test_wrong_update_order():
    raise NotImplementedError


def test_create_before_delete_is_over():
    raise NotImplementedError
