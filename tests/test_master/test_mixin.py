from __future__ import unicode_literals

import pytest
from uuid import uuid4

from django.db.models import CharField, IntegerField
from django.utils.timezone import now

from dj_cqrs.constants import SignalType
from dj_cqrs.metas import MasterMeta
from tests.dj_master import models
from tests.utils import assert_is_sub_dict, assert_publisher_once_called_with_args


def test_cqrs_fields_non_existing_field(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_FIELDS = ('char_field', 'integer_field')

            char_field = CharField(max_length=100, primary_key=True)
            int_field = IntegerField()

            _meta = mocker.MagicMock(concrete_fields=(char_field, int_field), private_fields=())
            _meta.pk.name = 'char_field'

        MasterMeta._check_cqrs_fields(Cls)

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

        MasterMeta._check_cqrs_fields(Cls)

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

        MasterMeta._check_cqrs_fields(Cls)

    assert str(e.value) == 'Duplicate names in CQRS_FIELDS field for model Cls.'


@pytest.mark.django_db
def test_to_cqrs_dict_has_cqrs_fields():
    m = models.AutoFieldsModel.objects.create()
    dct = m.to_cqrs_dict()
    assert dct['cqrs_revision'] == 0 and dct['cqrs_updated'] is not None


def test_to_cqrs_dict_basic_types():
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
    assert_is_sub_dict({
        'int_field': 1,
        'bool_field': False,
        'char_field': 'str',
        'date_field': None,
        'datetime_field': dt,
        'float_field': 1.23,
        'url_field': 'http://example.com',
        'uuid_field': uid,
    }, m.to_cqrs_dict())


def test_to_cqrs_dict_all_fields():
    m = models.AllFieldsModel(char_field='str')
    assert_is_sub_dict({'id': None, 'int_field': None, 'char_field': 'str'}, m.to_cqrs_dict())


def test_to_cqrs_dict_chosen_fields():
    m = models.ChosenFieldsModel(float_field=1.23)
    assert_is_sub_dict({'char_field': None, 'id': None}, m.to_cqrs_dict())


@pytest.mark.django_db
def test_to_cqrs_dict_auto_fields():
    m = models.AutoFieldsModel()
    assert_is_sub_dict({'id': None, 'created': None, 'updated': None}, m.to_cqrs_dict())

    m.save()
    cqrs_dct = m.to_cqrs_dict()
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
    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE, models.ChosenFieldsModel.CQRS_ID, {'char_field': 'old', 'id': 1}, 1,
    )


@pytest.mark.django_db
def test_cqrs_sync(mocker):
    m = models.ChosenFieldsModel.objects.create(char_field='old')
    m.char_field = 'new'
    m.save(update_fields=['char_field'])

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    assert m.cqrs_sync()
    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE, models.ChosenFieldsModel.CQRS_ID, {'char_field': 'new', 'id': 1}, 1,
    )


@pytest.mark.django_db
def test_create():
    for _ in range(2):
        m = models.AutoFieldsModel.objects.create()
        assert m.cqrs_revision == 0
        assert m.cqrs_updated is not None


@pytest.mark.django_db
def test_update():
    m = models.AutoFieldsModel.objects.create()
    cqrs_updated = m.cqrs_updated

    for i in range(1, 3):
        m.save()
        m.refresh_from_db()

        assert m.cqrs_revision == i

        assert m.cqrs_updated > cqrs_updated
        cqrs_updated = m.cqrs_updated
