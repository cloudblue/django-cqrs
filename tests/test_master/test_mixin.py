#  Copyright © 2022 Ingram Micro Inc. All rights reserved.

from datetime import timedelta
from time import sleep
from uuid import uuid4

from dj_cqrs.constants import (
    DEFAULT_MASTER_AUTO_UPDATE_FIELDS,
    DEFAULT_MASTER_MESSAGE_TTL,
    FIELDS_TRACKER_FIELD_NAME,
    SignalType,
)
from dj_cqrs.metas import MasterMeta

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import CharField, F, IntegerField
from django.utils.timezone import now

import pytest

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
@pytest.mark.skipif(settings.DB_ENGINE != 'sqlite', reason='sqlite only')
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
def test_cqrs_sync_optimized_for_class_serialization(mocker, django_assert_num_queries):
    models.Author.objects.create(
        id=5,
        name='hi',
        publisher=models.Publisher.objects.create(id=1, name='pub'),
    )
    m = models.Author.relate_cqrs_serialization(models.Author.objects.all()).first()

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    with django_assert_num_queries(0):
        assert m.cqrs_sync()

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SYNC,
        models.Author.CQRS_ID,
        {'id': 5, 'name': 'hi', 'publisher': {'id': 1, 'name': 'pub'}},
        5,
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


@pytest.mark.django_db(transaction=True)
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

    # 0 - Transaction start (SQLite only)
    # 1 - Publisher
    # 2 - Author
    # 3-4 - Books
    # 5-6 - Serialization with prefetch_related
    query_counter = 7 if settings.DB_ENGINE == 'sqlite' else 6
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
                'name': 'new',
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
    assert tracked_data == {'cqrs_revision': None, 'char_field': None}
    assert tracked_data is not None
    assert 'char_field' in tracked_data
    assert tracked_data['char_field'] is None

    instance.char_field = 'New Value'
    instance.save()
    tracked_data = instance.get_tracked_fields_data()
    assert 'char_field' in tracked_data
    assert tracked_data['char_field'] == 'Value'
    assert publisher_mock.call_args[0][0].previous_data == tracked_data
    assert tracked_data == {'cqrs_revision': 0, 'char_field': 'Value'}


@pytest.mark.django_db(transaction=True)
def test_cqrs_tracked_fields_date_and_datetime_tracking(mocker):
    old_dt = now()
    old_d = (old_dt + timedelta(days=1)).date()

    models.BasicFieldsModel.objects.create(
        int_field=1,
        datetime_field=old_dt,
        date_field=old_d,
    )

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    instance = models.BasicFieldsModel.objects.first()
    instance.datetime_field = now()
    instance.date_field = now().date()
    instance.save()

    tracked_data = instance.get_tracked_fields_data()
    assert publisher_mock.call_args[0][0].previous_data == tracked_data == {
        'cqrs_revision': 0, 'datetime_field': str(old_dt), 'date_field': str(old_d),
    }


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
    assert 'content_type' not in previous_data

    for prev_data_key in ('object_id', 'cqrs_revision', 'content_type_id'):
        assert previous_data[prev_data_key] is None

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


@pytest.mark.django_db(transaction=True)
def test_transaction_instance_saved_once_simple_case(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    i0 = models.TrackedFieldsChildModel.objects.create(char_field='old')
    with transaction.atomic():
        i1 = models.TrackedFieldsParentModel.objects.create(char_field='1')
        i1.char_field = '2'
        i1.save()

        i2 = models.TrackedFieldsParentModel(char_field='a')
        i2.save()

        i3 = models.TrackedFieldsChildModel.objects.create(char_field='.')

        i0.char_field = 'new'
        i0.save()

    assert publisher_mock.call_count == 5

    for i in [i0, i1, i2, i3]:
        i.refresh_from_db()
    assert i0.cqrs_revision == 1
    assert i1.cqrs_revision == 0
    assert i2.cqrs_revision == 0
    assert i3.cqrs_revision == 0

    mapper = (
        (i0.pk, 0, 'old', None),
        (i1.pk, 0, '2', None),
        (i2.pk, 0, 'a', None),
        (i3.pk, 0, '.', None),
        (i0.pk, 1, 'new', 'old'),
    )
    for index, call in enumerate(publisher_mock.call_args_list):
        payload = call[0][0]
        expected_data = mapper[index]

        assert payload.pk == expected_data[0]
        assert payload.instance_data['cqrs_revision'] == expected_data[1]
        assert payload.instance_data['char_field'] == expected_data[2]
        assert payload.previous_data['char_field'] == expected_data[3]


@pytest.mark.django_db(transaction=True)
def test_transaction_instance_saved_multiple_times_previous_data(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    instance = models.TrackedFieldsParentModel.objects.create(char_field='db_value')

    with transaction.atomic():
        instance.refresh_from_db()
        instance.char_field = 'save_1'
        instance.save()
        instance.char_field = 'save_2'
        instance.save()

    assert publisher_mock.call_count == 2
    payload_create = publisher_mock.call_args_list[0][0][0]
    payload_update = publisher_mock.call_args_list[1][0][0]
    assert payload_create.instance_data['char_field'] == 'db_value'
    assert payload_create.previous_data['char_field'] is None
    assert payload_update.instance_data['char_field'] == 'save_2'
    assert payload_update.previous_data['char_field'] == 'db_value'


@pytest.mark.django_db(transaction=True)
def test_cqrs_saves_count_lifecycle():
    instance = models.TrackedFieldsParentModel(char_field='1')
    instance.reset_cqrs_saves_count()
    assert instance.cqrs_saves_count == 0
    assert instance.is_initial_cqrs_save

    instance.save()
    assert instance.cqrs_saves_count == 0
    assert instance.is_initial_cqrs_save

    instance.save()
    assert instance.cqrs_saves_count == 0
    assert instance.is_initial_cqrs_save

    instance.refresh_from_db()
    assert instance.cqrs_saves_count == 0
    assert instance.is_initial_cqrs_save

    with transaction.atomic():
        instance.save()
        assert instance.cqrs_saves_count == 1
        assert instance.is_initial_cqrs_save

        instance.save()
        assert instance.cqrs_saves_count == 2
        assert not instance.is_initial_cqrs_save

        instance.refresh_from_db()
        assert instance.cqrs_saves_count == 2
        assert not instance.is_initial_cqrs_save

        same_db_object_other_instance = models.TrackedFieldsParentModel.objects.first()
        assert same_db_object_other_instance.pk == instance.pk
        assert same_db_object_other_instance.cqrs_saves_count == 0
        assert same_db_object_other_instance.is_initial_cqrs_save

        same_db_object_other_instance.save()
        assert same_db_object_other_instance.cqrs_saves_count == 1
        assert same_db_object_other_instance.is_initial_cqrs_save

        same_db_object_other_instance.reset_cqrs_saves_count()
        assert same_db_object_other_instance.cqrs_saves_count == 0
        assert same_db_object_other_instance.is_initial_cqrs_save

        same_db_object_other_instance.save()
        assert same_db_object_other_instance.cqrs_saves_count == 1
        assert same_db_object_other_instance.is_initial_cqrs_save

    assert instance.cqrs_saves_count == 0
    assert same_db_object_other_instance.cqrs_saves_count == 0


@pytest.mark.django_db(transaction=True)
def test_sequential_transactions(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    with transaction.atomic():
        instance = models.TrackedFieldsParentModel.objects.create(char_field='1')

    with transaction.atomic():
        instance.char_field = '3'
        instance.save()

        transaction.set_rollback(True)
        instance.reset_cqrs_saves_count()

    with transaction.atomic():
        instance.char_field = '2'
        instance.save()

    instance.refresh_from_db()

    assert publisher_mock.call_count == 2
    assert instance.cqrs_revision == 1
    assert publisher_mock.call_args_list[0][0][0].instance_data['char_field'] == '1'
    assert publisher_mock.call_args_list[1][0][0].instance_data['char_field'] == '2'


@pytest.mark.django_db(transaction=True)
def test_get_custom_cqrs_delete_data(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    m = models.SimplestModel.objects.create(id=1)
    m.get_custom_cqrs_delete_data = lambda *args: {'1': '2'}
    m.delete()

    payload = publisher_mock.call_args_list[1][0][0]
    assert payload.signal_type == SignalType.DELETE
    assert payload.instance_data['id'] == 1
    assert payload.instance_data['cqrs_revision'] == 1
    assert payload.instance_data['custom'] == {'1': '2'}


@pytest.mark.django_db(transaction=True)
def test_save_update_fields_no_cqrs_fields_default_behavior(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    instance = models.SimplestModel.objects.create(id=1)
    publisher_mock.reset_mock()

    instance.name = 'New'
    instance.save(update_fields=['name'])
    instance.refresh_from_db()

    assert publisher_mock.call_count == 0
    assert instance.cqrs_revision == 0
    assert instance.name == 'New'


@pytest.mark.django_db(transaction=True)
def test_save_update_fields_no_cqrs_fields_global_flag_changed(mocker, settings):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    instance = models.SimplestModel.objects.create(id=1)
    previous_cqrs_updated = instance.cqrs_updated
    publisher_mock.reset_mock()

    sleep(0.1)

    settings.CQRS = {
        'transport': 'tests.dj.transport.TransportStub',
        'master': {
            'CQRS_AUTO_UPDATE_FIELDS': not DEFAULT_MASTER_AUTO_UPDATE_FIELDS,
            'CQRS_MESSAGE_TTL': DEFAULT_MASTER_MESSAGE_TTL,
            'correlation_function': None,
            'meta_function': None,
        },
    }
    instance.name = 'New'
    instance.save(update_fields=['name'])

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE,
        models.SimplestModel.CQRS_ID,
        {'id': 1, 'name': 'New', 'cqrs_revision': 1},
        1,
    )

    assert instance.cqrs_updated > previous_cqrs_updated

    instance.refresh_from_db()
    assert instance.name == 'New'


@pytest.mark.django_db(transaction=True)
def test_save_update_fields_with_cqrs_fields(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    instance = models.SimplestModel.objects.create(id=1, name='Old')
    previous_cqrs_updated = instance.cqrs_updated
    publisher_mock.reset_mock()

    sleep(0.1)

    instance.name = 'New'
    instance.cqrs_revision = F('cqrs_revision') + 1
    instance.save(update_fields=['name', 'cqrs_revision', 'cqrs_updated'], update_cqrs_fields=False)

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE,
        models.SimplestModel.CQRS_ID,
        {'id': 1, 'name': 'New', 'cqrs_revision': 1},
        1,
    )

    assert instance.cqrs_updated > previous_cqrs_updated

    instance.refresh_from_db()
    assert instance.name == 'New'


@pytest.mark.django_db(transaction=True)
def test_save_update_fields_with_update_cqrs_fields_flag(mocker):
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    instance = models.SimplestModel.objects.create(id=1)
    previous_cqrs_updated = instance.cqrs_updated
    publisher_mock.reset_mock()

    sleep(0.1)

    instance.name = 'New'
    instance.save(update_fields=['name'], update_cqrs_fields=True)

    assert_publisher_once_called_with_args(
        publisher_mock,
        SignalType.SAVE,
        models.SimplestModel.CQRS_ID,
        {'id': 1, 'name': 'New', 'cqrs_revision': 1},
        1,
    )

    assert instance.cqrs_updated > previous_cqrs_updated

    instance.refresh_from_db()
    assert instance.name == 'New'


@pytest.mark.django_db(transaction=True)
def test_get_cqrs_meta_global_meta_function(mocker, settings):
    f = mocker.MagicMock()
    f.return_value = {1: 2}

    settings.CQRS['master']['meta_function'] = f
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    obj = models.SimplestModel.objects.create(id=1)

    assert publisher_mock.call_args[0][0].meta == {1: 2}
    f.assert_called_once_with(
        instance_data={
            'cqrs_revision': 0,
            'cqrs_updated': str(obj.cqrs_updated),
            'id': 1,
            'name': None,
        },
        previous_data=None,
        signal_type=SignalType.SAVE,
    )


@pytest.mark.django_db(transaction=True)
def test_get_cqrs_meta_custom_function(mocker, settings):
    f = mocker.MagicMock()

    settings.CQRS['master']['meta_function'] = f
    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')

    obj = models.SimplestModel(id=1)
    obj.get_cqrs_meta = lambda **k: {'test': []}
    obj.save()

    assert publisher_mock.call_args[0][0].meta == {'test': []}
    f.assert_not_called()
