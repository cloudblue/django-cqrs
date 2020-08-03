#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest
from uuid import uuid4

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import CharField, IntegerField, F
from django.utils.timezone import now

from dj_cqrs.constants import SignalType, FIELDS_TRACKER_FIELD_NAME
from dj_cqrs.metas import MasterMeta
from tests.dj_master import models
from tests.dj_master.serializers import AuthorSerializer
from tests.utils import (
    assert_is_sub_dict,
    assert_publisher_once_called_with_args,
    assert_tracked_fields,
)


class MasterMetaTest(MasterMeta):
    @classmethod
    def check_cqrs_fields(cls, model_cls):
        return cls._check_cqrs_fields(model_cls)

    @classmethod
    def check_correct_configuration(cls, model_cls):
        return cls._check_correct_configuration(model_cls)

    @classmethod
    def check_cqrs_tracked_fields(cls, model_cls):
        return cls._check_cqrs_tracked_fields(model_cls)


def test_cqrs_fields_non_existing_field(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_FIELDS = ('char_field', 'integer_field')

            char_field = CharField(max_length=100, primary_key=True)
            int_field = IntegerField()

            _meta = mocker.MagicMock(concrete_fields=(char_field, int_field), private_fields=())
            _meta.pk.name = 'char_field'

        MasterMetaTest.check_cqrs_fields(Cls)

    assert str(e.value) == 'CQRS_FIELDS field is not correctly set for model Cls.'


def test_cqrs_fields_id_is_not_included(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_FIELDS = ('int_field',)

            char_field = CharField(max_length=100, primary_key=True)
            int_field = IntegerField()

            _meta = mocker.MagicMock(concrete_fields=(char_field, int_field), private_fields=())
            _meta.pk.name = 'char_field'

        MasterMetaTest.check_cqrs_fields(Cls)

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

        MasterMetaTest.check_cqrs_fields(Cls)

    assert str(e.value) == 'Duplicate names in CQRS_FIELDS field for model Cls.'


def test_cqrs_bad_configuration(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_FIELDS = ('char_field',)
            CQRS_SERIALIZER = 'path.to.serializer'

            char_field = CharField(max_length=100, primary_key=True)

            _meta = mocker.MagicMock(concrete_fields=(char_field,), private_fields=())
            _meta.pk.name = 'char_field'

        MasterMetaTest.check_correct_configuration(Cls)

    assert "CQRS_FIELDS can't be set together with CQRS_SERIALIZER." in str(e.value)


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
        'datetime_field': str(dt),
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


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_cqrs_sync_not_saved(mocker):
    m = models.ChosenFieldsModel.objects.create(char_field='old')
    m.name = 'new'

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    assert m.cqrs_sync()

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SYNC, models.ChosenFieldsModel.CQRS_ID, {'char_field': 'old', 'id': m.pk}, m.pk,
    )


@pytest.mark.django_db(transaction=True)
def test_cqrs_sync(mocker):
    m = models.ChosenFieldsModel.objects.create(char_field='old')
    m.char_field = 'new'
    m.save(update_fields=['char_field'])

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    assert m.cqrs_sync()

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SYNC, models.ChosenFieldsModel.CQRS_ID, {'char_field': 'new', 'id': m.pk}, m.pk,
    )


@pytest.mark.django_db(transaction=True)
def test_is_sync_instance(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    out_instance = models.FilteredSimplestModel.objects.create(name='a')
    in_instance = models.FilteredSimplestModel.objects.create(name='title')

    instances = (out_instance, in_instance)
    for instance in instances:
        assert instance.cqrs_revision == 0

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE,
        models.FilteredSimplestModel.CQRS_ID,
        {'name': 'title', 'id': in_instance.pk},
        in_instance.pk,
    )
    publisher_mock.reset_mock()

    in_instance.name = 'longer title'
    for instance in instances:
        instance.save()
        instance.refresh_from_db()

        assert instance.cqrs_revision == 1

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE,
        models.FilteredSimplestModel.CQRS_ID,
        {'name': 'longer title', 'id': in_instance.pk},
        in_instance.pk,
    )
    publisher_mock.reset_mock()

    out_instance.name = 'long'
    in_instance.name = 's'
    for instance in instances:
        instance.save()
        instance.refresh_from_db()

        assert instance.cqrs_revision == 2

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE,
        models.FilteredSimplestModel.CQRS_ID,
        {'name': 'long', 'id': out_instance.pk},
        out_instance.pk,
    )

    publisher_mock.reset_mock()
    in_instance.delete()
    assert publisher_mock.call_count == 0

    out_instance.delete()
    assert publisher_mock.call_count == 1


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


@pytest.mark.django_db(transaction=True)
def test_transaction_rollbacked(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    try:
        with transaction.atomic():
            models.BasicFieldsModel.objects.create(
                int_field=1,
                char_field='str',
            )
            raise ValueError

    except ValueError:
        publisher_mock.assert_not_called()


@pytest.mark.django_db(transaction=True)
def test_transaction_commited(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    with transaction.atomic():
        models.BasicFieldsModel.objects.create(
            int_field=1,
            char_field='str',
        )

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE, models.BasicFieldsModel.CQRS_ID, {'char_field': 'str', 'int_field': 1}, 1,
    )


@pytest.mark.django_db(transaction=True)
def test_transaction_rollbacked_to_savepoint(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    with transaction.atomic():
        models.BasicFieldsModel.objects.create(
            int_field=1,
            char_field='str',
        )

        try:
            with transaction.atomic(savepoint=True):
                raise ValueError
        except ValueError:
            pass

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE, models.BasicFieldsModel.CQRS_ID, {'char_field': 'str', 'int_field': 1}, 1,
    )


@pytest.mark.django_db(transaction=True)
def test_serialization_no_related_instance(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    models.Author.objects.create(id=1, name='author', publisher=None)

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE, models.Author.CQRS_ID,
        {
            'id': 1,
            'name': 'author',
            'publisher': None,
            'books': [],
            'cqrs_revision': 0,
        }, 1,
    )


@pytest.mark.django_db(transaction=True)
def test_save_serialization(mocker, django_assert_num_queries):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    # 0 - Transaction start
    # 1 - Publisher
    # 2 - Author
    # 3-4 - Books
    # 5-6 - Serialization with prefetch_related
    query_counter = 7
    with django_assert_num_queries(query_counter):
        with transaction.atomic():
            publisher = models.Publisher.objects.create(id=1, name='publisher')
            author = models.Author.objects.create(id=1, name='author', publisher=publisher)
            for index in range(1, 3):
                models.Book.objects.create(id=index, title=str(index), author=author)

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE, models.Author.CQRS_ID,
        {
            'id': 1,
            'name': 'author',
            'publisher': {
                'id': 1,
                'name': 'publisher',
            },
            'books': [{
                'id': 1,
                'name': '1',
            }, {
                'id': 2,
                'name': '2',
            }],
            'cqrs_revision': 0,
        }, 1,
    )


@pytest.mark.django_db(transaction=True)
def test_delete_serialization():
    m = models.Author.objects.create(id=1, name='author', publisher=None)
    assert models.Author.objects.count() == 1

    m.delete()
    assert models.Author.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_create_from_related_table(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    author = models.Author.objects.create(id=1, name='author', publisher=None)

    with transaction.atomic():
        models.Book.objects.create(id=1, title='title', author=author)

        # Calling author.cqrs_sync() would result in a wrong cqrs_revision!
        author.save()

    assert publisher_mock.call_count == 2
    assert_is_sub_dict(
        {
            'id': 1,
            'name': 'author',
            'publisher': None,
            'books': [{
                'id': 1,
                'name': 'title',
            }],
            'cqrs_revision': 1,
        },
        publisher_mock.call_args[0][0].instance_data,
    )


@pytest.mark.django_db(transaction=True)
def test_update_from_related_table(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    with transaction.atomic():
        publisher = models.Publisher.objects.create(id=1, name='publisher')
        author = models.Author.objects.create(id=1, name='author', publisher=publisher)

    with transaction.atomic():
        publisher.name = 'new'
        publisher.save()

        author.save()

    assert publisher_mock.call_count == 2
    assert_is_sub_dict(
        {
            'id': 1,
            'name': 'author',
            'publisher': {
                'id': 1,
                'name': 'new'
            },
            'books': [],
            'cqrs_revision': 1,
        },
        publisher_mock.call_args[0][0].instance_data,
    )


@pytest.mark.django_db(transaction=True)
def test_to_cqrs_dict_serializer_ok():
    model = models.Author.objects.create(id=1)

    assert_is_sub_dict(AuthorSerializer(model).data, model.to_cqrs_dict())
    assert models.Author._cqrs_serializer_class == AuthorSerializer


@pytest.mark.django_db(transaction=True)
def test_to_cqrs_dict_serializer_import_error():
    with pytest.raises(ImportError) as e:
        with transaction.atomic():
            models.BadSerializationClassModel.objects.create(id=1)

    assert "CQRS_SERIALIZER can't be imported." in str(e)


@pytest.mark.django_db(transaction=True)
def test_to_cqrs_dict_serializer_bad_related_function():
    with pytest.raises(RuntimeError) as e:
        models.BadQuerySetSerializationClassModel.objects.create()

    assert "Couldn't serialize CQRS class (bad_queryset)." in str(e)


@pytest.mark.django_db(transaction=True)
def test_multiple_inheritance(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    models.NonMetaClassModel.objects.create(name='abc')

    assert publisher_mock.call_count == 1


@pytest.mark.django_db(transaction=True)
def test_non_sent(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    m = models.NonSentModel.objects.create()
    assert publisher_mock.call_count == 0
    m.refresh_from_db()
    assert m.cqrs_revision == 0

    m.save()
    assert publisher_mock.call_count == 0
    m.refresh_from_db()
    assert m.cqrs_revision == 1

    m.delete()
    assert publisher_mock.call_count == 0


def test_cqrs_tracked_fields_non_existing_field(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_TRACKED_FIELDS = ('char_field', 'integer_field')

            char_field = CharField(max_length=100, primary_key=True)
            int_field = IntegerField()

            _meta = mocker.MagicMock(concrete_fields=(char_field, int_field), private_fields=())
            _meta.pk.name = 'char_field'

        MasterMetaTest.check_cqrs_tracked_fields(Cls)

    assert str(e.value) == 'CQRS_TRACKED_FIELDS field is not correctly set for model Cls.'


def test_cqrs_tracked_fields_duplicates(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_TRACKED_FIELDS = ('char_field', 'char_field')

            char_field = CharField(max_length=100, primary_key=True)
            int_field = IntegerField()

            _meta = mocker.MagicMock(concrete_fields=(char_field, int_field), private_fields=())
            _meta.pk.name = 'char_field'

        MasterMetaTest.check_cqrs_tracked_fields(Cls)

    assert str(e.value) == 'Duplicate names in CQRS_TRACKED_FIELDS field for model Cls.'


def test_cqrs_tracked_fields_bad_configuration(mocker):
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRD_ID = 'ID'
            CQRS_TRACKED_FIELDS = 'bad_config'

            char_field = CharField(max_length=100, primary_key=True)
            int_field = IntegerField()

            _meta = mocker.MagicMock(concrete_fields=(char_field, int_field), private_fields=())
            _meta.pk.name = 'char_field'

        MasterMetaTest.check_cqrs_tracked_fields(Cls)

    assert str(e.value) == 'Model Cls: Invalid configuration for CQRS_TRACKED_FIELDS'


def test_cqrs_tracked_fields_model_has_tracker(mocker):
    instance = models.TrackedFieldsChildModel()
    tracker = getattr(instance, FIELDS_TRACKER_FIELD_NAME)
    assert tracker is not None


def test_cqrs_tracked_fields_related_fields(mocker):
    instance = models.TrackedFieldsChildModel()
    tracker = getattr(instance, FIELDS_TRACKER_FIELD_NAME)
    assert_tracked_fields(models.TrackedFieldsChildModel, tracker.fields)


def test_cqrs_tracked_fields_all_related_fields(mocker):
    instance = models.TrackedFieldsAllWithChildModel()
    tracker = getattr(instance, FIELDS_TRACKER_FIELD_NAME)
    assert_tracked_fields(models.TrackedFieldsAllWithChildModel, tracker.fields)


@pytest.mark.django_db(transaction=True)
def test_cqrs_tracked_fields_tracking(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    instance = models.TrackedFieldsParentModel()
    instance.char_field = 'Value'
    instance.save()
    tracked_data = instance.get_tracked_fields_data()
    assert publisher_mock.call_args[0][0].previous_data == tracked_data
    assert tracked_data is not None
    assert 'char_field' in tracked_data
    assert tracked_data['char_field'] is None
    instance.char_field = 'New Value'
    instance.save()
    tracked_data = instance.get_tracked_fields_data()
    assert 'char_field' in tracked_data
    assert tracked_data['char_field'] == 'Value'
    assert publisher_mock.call_args[0][0].previous_data == tracked_data


def test_mptt_cqrs_tracked_fields_model_has_tracker():
    instance = models.MPTTWithTrackingModel()
    tracker = getattr(instance, FIELDS_TRACKER_FIELD_NAME)
    assert tracker is not None


def test_mptt_cqrs_tracked_fields_related_fields():
    instance = models.MPTTWithTrackingModel()
    tracker = getattr(instance, FIELDS_TRACKER_FIELD_NAME)
    assert_tracked_fields(models.MPTTWithTrackingModel, tracker.fields)


@pytest.mark.django_db(transaction=True)
def test_f_expr():
    m = models.AllFieldsModel.objects.create(int_field=0, char_field='char')
    m.int_field = F('int_field') + 1
    m.save()

    cqrs_data = m.to_cqrs_dict()
    previous_data = m.get_tracked_fields_data()

    assert 'int_field' in cqrs_data
    assert cqrs_data['int_field'] == 1
    assert 'int_field' in previous_data
    assert previous_data['int_field'] == 0


@pytest.mark.django_db(transaction=True)
def test_generic_fk():
    sm = models.SimplestModel.objects.create(id=1, name='char')
    m = models.WithGenericFKModel.objects.create(content_object=sm)
    ct = ContentType.objects.get_for_model(models.SimplestModel)
    cqrs_data = m.to_cqrs_dict()
    previous_data = m.get_tracked_fields_data()

    assert 'content_object' not in cqrs_data
    assert 'content_type' in cqrs_data
    assert 'object_id' in cqrs_data
    assert cqrs_data['object_id'] == sm.pk
    assert cqrs_data['content_type'] == ct.pk

    assert 'content_object' not in previous_data
    assert 'content_type' in previous_data
    assert 'object_id' in previous_data

    sm1 = models.SimplestModel.objects.create(id=2, name='name')
    m.content_object = sm1
    m.save()
    previous_data = m.get_tracked_fields_data()

    assert 'content_object' not in previous_data
    assert 'content_type' not in previous_data
    assert previous_data['object_id'] == sm.pk


@pytest.mark.django_db(transaction=True)
def test_m2m_not_supported():
    m1 = models.M2MModel.objects.create(id=1, name='name')
    m2m = models.WithM2MModel.objects.create(char_field='test')
    m2m.m2m_field.add(m1)
    m2m.save()
    cqrs_data = m2m.to_cqrs_dict()

    assert 'm2m_field' not in cqrs_data
    assert 'char_field' in cqrs_data
