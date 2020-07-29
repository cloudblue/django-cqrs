#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest

from django.db.models import CharField, IntegerField
from django.utils.timezone import now

from dj_cqrs.metas import ReplicaMeta
from tests.dj_replica import models
from tests.utils import db_error


class ReplicaMetaTest(ReplicaMeta):
    @classmethod
    def check_cqrs_mapping(cls, model_cls):
        return cls._check_cqrs_mapping(model_cls)


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

        ReplicaMetaTest.check_cqrs_mapping(Cls)

    assert str(e.value) == 'CQRS_MAPPING field is not correctly set for model Cls.'


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

        ReplicaMetaTest.check_cqrs_mapping(Cls)

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

        ReplicaMetaTest.check_cqrs_mapping(Cls)

    assert str(e.value) == 'Duplicate names in CQRS_MAPPING field for model Cls.'


@pytest.mark.django_db
def test_create_simple():
    instance = models.BasicFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_revision': 0,
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
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
        'unexpected_field': 'value',
    })
    assert isinstance(instance, models.BasicFieldsModelRef)


@pytest.mark.django_db
def test_create_simple_insufficient_data(caplog):
    models.BasicFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
    })

    assert 'Not all required CQRS fields are provided in data (basic).' in caplog.text


@pytest.mark.django_db
def test_create_mapped(caplog):
    instance = models.MappedFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })
    assert isinstance(instance, models.MappedFieldsModelRef)

    instance.refresh_from_db()
    assert instance.id == 1
    assert instance.name == 'text'


@pytest.mark.django_db
def test_create_mapped_bad_mapping(caplog):
    models.BadMappingModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })

    assert 'Bad master-replica mapping for invalid_field (basic_3).' in caplog.text


@pytest.mark.django_db
def test_create_db_error(mocker, caplog):
    mocker.patch.object(models.BasicFieldsModelRef.objects, 'create', side_effect=db_error)

    models.BasicFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })
    assert 'CQRS create error: pk = 1 (basic).' in caplog.text


@pytest.mark.django_db
def test_update_ok():
    models.BasicFieldsModelRef.objects.create(**{
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })

    instance = models.BasicFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_revision': 1,
        'cqrs_updated': now(),
        'char_field': 'new_text',
        'float_field': 1.30,
    })

    assert isinstance(instance, models.BasicFieldsModelRef)

    instance.refresh_from_db()
    assert instance.int_field == 1
    assert instance.char_field == 'new_text'
    assert instance.float_field == 1.30


@pytest.mark.django_db
def test_update_db_error(mocker, caplog):
    models.BasicFieldsModelRef.objects.create(**{
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })

    mocker.patch.object(models.BasicFieldsModelRef, 'save', side_effect=db_error)

    models.BasicFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_revision': 1,
        'cqrs_updated': now(),
        'char_field': 'text',
    })
    assert 'CQRS update error: pk = 1, cqrs_revision = 1 (basic).' in caplog.text


@pytest.mark.django_db
def test_delete_ok():
    dt = now()
    models.BasicFieldsModelRef.objects.create(**{
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': dt,
        'char_field': 'text',
    })

    is_deleted = models.BasicFieldsModelRef.cqrs_delete({
        'id': 1,
        'cqrs_revision': 0,
        'cqrs_updated': dt,
    })

    assert is_deleted
    assert models.BasicFieldsModelRef.objects.count() == 0


@pytest.mark.django_db
def test_delete_non_existing_id():
    is_deleted = models.BasicFieldsModelRef.cqrs_delete({
        'id': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
    })

    assert is_deleted
    assert models.BasicFieldsModelRef.objects.count() == 0


@pytest.mark.django_db
def test_delete_db_error(mocker, caplog):
    mocker.patch.object(models.BasicFieldsModelRef.objects, 'filter', side_effect=db_error)

    is_deleted = models.BasicFieldsModelRef.cqrs_delete({
        'id': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
    })

    assert not is_deleted
    assert 'CQRS delete error: pk = 1' in caplog.text


@pytest.mark.django_db
def test_save_bad_master_data_field_type(caplog):
    models.BadTypeModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'datetime_field': now(),
    })
    assert 'CQRS create error: pk = 1 (basic_1).' in caplog.text


@pytest.mark.django_db
def test_save_no_pk_in_master_data(caplog):
    models.BasicFieldsModelRef.cqrs_save({
        'id': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })

    assert 'CQRS PK is not provided in data (basic).' in caplog.text


@pytest.mark.django_db
def test_save_no_cqrs_fields_in_master_data(caplog):
    models.BasicFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_revision': 0,
        'char_field': 'text',
    })

    assert 'CQRS sync fields are not provided in data (basic).' in caplog.text


@pytest.mark.django_db
def test_delete_no_id_in_master_data(caplog):
    is_deleted = models.BasicFieldsModelRef.cqrs_delete({
        'cqrs_revision': 0,
        'cqrs_updated': now(),
    })

    assert not is_deleted
    assert 'CQRS PK is not provided in data (basic).' in caplog.text


@pytest.mark.django_db
def test_delete_no_cqrs_fields_in_master_data(caplog):
    is_deleted = models.BasicFieldsModelRef.cqrs_delete({
        'id': 1,
        'cqrs_revision': 0,
    })

    assert not is_deleted
    assert 'CQRS sync fields are not provided in data (basic).' in caplog.text


@pytest.mark.django_db(transaction=True)
def test_update_before_create_is_over(caplog):
    create_data = {
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    }

    update_data = {
        'int_field': 1,
        'cqrs_revision': 1,
        'cqrs_updated': now(),
        'char_field': 'new_text',
    }

    updated_instance = models.BasicFieldsModelRef.cqrs_save(update_data)
    created_instance = models.BasicFieldsModelRef.cqrs.create_instance(create_data)
    updated_instance.refresh_from_db()

    assert updated_instance.cqrs_revision == 1
    assert updated_instance.char_field == 'new_text'
    assert not created_instance
    assert 'Potentially wrong CQRS sync order: pk = 1, cqrs_revision = 0 (basic).' in caplog.text
    assert 'CQRS create error: pk = 1 (basic).' in caplog.text


@pytest.mark.django_db(transaction=True)
def test_wrong_update_order(caplog):
    models.BasicFieldsModelRef.objects.create(**{
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })

    update_data_1 = {
        'int_field': 1,
        'cqrs_revision': 1,
        'cqrs_updated': now(),
        'char_field': 'new_text_1',
    }

    update_data_2 = {
        'int_field': 1,
        'cqrs_revision': 2,
        'cqrs_updated': now(),
        'char_field': 'new_text_2',
    }

    earlier_instance = models.BasicFieldsModelRef.cqrs_save(update_data_2)
    later_instance = models.BasicFieldsModelRef.cqrs_save(update_data_1)
    earlier_instance.refresh_from_db()

    assert earlier_instance.cqrs_revision == 2
    assert earlier_instance.char_field == 'new_text_2'
    assert later_instance
    assert 'Wrong CQRS sync order: pk = 1, cqrs_revision = new 1 / existing 2 (basic).' in \
        caplog.text


@pytest.mark.django_db(transaction=True)
def test_de_duplication(caplog):
    models.BasicFieldsModelRef.objects.create(**{
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })

    update_data = {
        'int_field': 1,
        'cqrs_revision': 1,
        'cqrs_updated': now(),
        'char_field': 'new_text',
    }

    earlier_instance = models.BasicFieldsModelRef.cqrs_save(update_data)
    duplicate_instance = models.BasicFieldsModelRef.cqrs_save(update_data)

    assert earlier_instance.cqrs_revision == 1
    assert earlier_instance.char_field == 'new_text'
    assert duplicate_instance.cqrs_revision == 1
    assert duplicate_instance.char_field == 'new_text'
    assert 'Received duplicate CQRS data: pk = 1, cqrs_revision = 1 (basic).' in caplog.text


@pytest.mark.django_db(transaction=True)
def test_create_before_delete_is_over(caplog):
    # This situation may extremely rarely happen, if the IDs are not auto incremented on master
    #  and are not unique in the infinite timeline.
    # This will lead to expected inconsistency.

    models.BasicFieldsModelRef.objects.create(**{
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })

    delete_data = {
        'id': 1,
        'cqrs_revision': 1,
        'cqrs_updated': now(),
    }
    new_create_data = {
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'other',
    }

    models.BasicFieldsModelRef.cqrs_save(new_create_data)
    is_deleted = models.BasicFieldsModelRef.cqrs_delete(delete_data)

    assert 'Received duplicate CQRS data: pk = 1, cqrs_revision = 0 (basic).' in caplog.text
    assert 'CQRS potential creation race condition: pk = 1 (basic).' in caplog.text
    assert is_deleted


@pytest.mark.django_db
def test_updates_were_lost(caplog):
    models.BasicFieldsModelRef.objects.create(**{
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    })

    models.BasicFieldsModelRef.cqrs_save({
        'int_field': 1,
        'cqrs_revision': 5,
        'cqrs_updated': now(),
        'char_field': 'text1',
    })

    assert 'Lost or filtered out 4 CQRS packages: pk = 1, cqrs_revision = 5 (basic)' in caplog.text


@pytest.mark.django_db()
def test_tracked_fields_mapped(mocker):
    cqrs_update_mock = mocker.patch.object(models.MappedFieldsModelRef, 'cqrs_update')
    first_payload = {
        'int_field': 1,
        'cqrs_revision': 0,
        'cqrs_updated': now(),
        'char_field': 'text',
    }

    second_payload = {
        'int_field': 1,
        'cqrs_revision': 1,
        'cqrs_updated': now(),
        'char_field': 'new_text',
    }

    models.MappedFieldsModelRef.cqrs_save(first_payload)
    models.MappedFieldsModelRef.cqrs_save(second_payload, previous_data={'char_field': 'text'})
    assert cqrs_update_mock.call_count == 1
    _, kwargs = cqrs_update_mock.call_args
    assert 'previous_data' in kwargs
    assert kwargs['previous_data'] == {'name': 'text'}
