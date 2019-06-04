from __future__ import unicode_literals

import pytest
from uuid import uuid4

from django.db.models import CharField, IntegerField
from django.utils.timezone import now

from dj_cqrs.constants import SignalType
from dj_cqrs.mixins import _MasterMeta
from tests.dj_master import models


def test_cqrs_fields_non_existing_field(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_FIELDS = ('char_field', 'integer_field')

            char_field = CharField(max_length=100, primary_key=True)
            int_field = IntegerField()

            _meta = mocker.MagicMock(concrete_fields=(char_field, int_field), private_fields=())
            _meta.pk.name = 'char_field'

        _MasterMeta._check_cqrs_fields(Cls)

    assert str(e.value) == 'CQRS_FIELDS field is not setup correctly for model Cls.'


def test_cqrs_fields_id_is_not_included(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_FIELDS = ('int_field',)

            char_field = CharField(max_length=100, primary_key=True)
            int_field = IntegerField()

            _meta = mocker.MagicMock(concrete_fields=(char_field, int_field), private_fields=())
            _meta.pk.name = 'char_field'

        _MasterMeta._check_cqrs_fields(Cls)

    assert str(e.value) == 'PK is not in CQRS_FIELDS for model Cls.'


def test_cqrs_fields_duplicates(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_FIELDS = ('char_field', 'char_field')

            char_field = CharField(max_length=100, primary_key=True)
            int_field = IntegerField()

            _meta = mocker.MagicMock(concrete_fields=(char_field, int_field), private_fields=())
            _meta.pk.name = 'char_field'

        _MasterMeta._check_cqrs_fields(Cls)

    assert str(e.value) == 'Duplicate names in CQRS_FIELDS field for model Cls.'


def test_model_to_cqrs_dict_basic_types():
    dt = now()
    uid = uuid4()
    m = models.BasicFieldsModel(
        int_field=1,
        bool_field=False,
        char_field='str',
        date_field=None,
        datetime_field=dt,
        float_field=1.23,
        url_field='http://example.com',
        uuid_field=uid,
    )
    assert m.model_to_cqrs_dict() == {
        'int_field': 1,
        'bool_field': False,
        'char_field': 'str',
        'date_field': None,
        'datetime_field': dt,
        'float_field': 1.23,
        'url_field': 'http://example.com',
        'uuid_field': uid,
    }


def test_model_to_cqrs_dict_all_fields():
    m = models.AllFieldsModel(char_field='str')
    assert m.model_to_cqrs_dict() == {'id': None, 'int_field': None, 'char_field': 'str'}


def test_model_to_cqrs_dict_chosen_fields():
    m = models.ChosenFieldsModel(float_field=1.23)
    assert m.model_to_cqrs_dict() == {'char_field': None, 'id': None}


@pytest.mark.django_db
def test_model_to_cqrs_dict_auto_fields():
    m = models.AutoFieldsModel()
    assert m.model_to_cqrs_dict() == {'id': None, 'created': None, 'updated': None}

    m.save()
    cqrs_dct = m.model_to_cqrs_dict()
    for key in ('id', 'created', 'updated'):
        assert cqrs_dct[key] is not None


def test_cqrs_sync_not_created():
    m = models.BasicFieldsModel()
    assert not m.cqrs_sync()


@pytest.mark.django_db
def test_cqrs_sync_cant_refresh_model():
    m = models.SimplestModel.objects.create()
    assert not m.cqrs_sync()


@pytest.mark.django_db
def test_cqrs_sync_not_saved(mocker):
    m = models.ChosenFieldsModel.objects.create(char_field='old')
    m.name = 'new'

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    assert m.cqrs_sync()
    publisher_mock.assert_called_once_with(
        SignalType.SAVE, models.ChosenFieldsModel.CQRS_ID, {'char_field': 'old', 'id': 1},
    )


@pytest.mark.django_db
def test_cqrs_sync(mocker):
    m = models.ChosenFieldsModel.objects.create(char_field='old')
    m.char_field = 'new'
    m.save(update_fields=['char_field'])

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    assert m.cqrs_sync()
    publisher_mock.assert_called_once_with(
        SignalType.SAVE, models.ChosenFieldsModel.CQRS_ID, {'char_field': 'new', 'id': 1},
    )
