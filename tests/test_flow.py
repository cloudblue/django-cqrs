#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest
from django.db import transaction

from tests.dj_master import models as master_models
from tests.dj_replica import models as replica_models


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


@pytest.mark.django_db(transaction=True)
def test_create_serialized():
    with transaction.atomic():
        publisher = master_models.Publisher.objects.create(id=1, name='publisher')
        author = master_models.Author.objects.create(id=1, name='author', publisher=publisher)
        for index in range(1, 3):
            master_models.Book.objects.create(id=index, title=str(index), author=author)

    replica_publisher = replica_models.Publisher.objects.first()
    replica_author = replica_models.AuthorRef.objects.first()
    books = list(replica_models.Book.objects.all())

    assert replica_publisher.id == 1
    assert replica_publisher.name == 'publisher'

    assert replica_author.id == 1
    assert replica_author.name == 'author'
    assert replica_author.publisher == replica_publisher
    assert replica_author.cqrs_revision == 0

    assert len(books) == 2
    assert {1} == {book.author_id for book in books}
    assert {1, 2} == {book.id for book in books}


@pytest.mark.django_db(transaction=True)
def test_update_serialized():
    author = master_models.Author.objects.create(id=1, name='author')
    author.refresh_from_db()

    assert replica_models.AuthorRef.objects.count() == 1

    with transaction.atomic():
        publisher = master_models.Publisher.objects.create(id=1, name='publisher')

        author.publisher = publisher
        author.save()

    replica_publisher = replica_models.Publisher.objects.first()
    replica_author = replica_models.AuthorRef.objects.first()

    assert replica_publisher.id == 1
    assert replica_publisher.name == 'publisher'

    assert replica_author.id == 1
    assert replica_author.name == 'author'
    assert replica_author.publisher == replica_publisher
    assert replica_author.cqrs_revision == 1


@pytest.mark.django_db(transaction=True)
def test_delete_serialized():
    with transaction.atomic():
        author = master_models.Author.objects.create(id=1, name='author')
        for index in range(1, 3):
            master_models.Book.objects.create(id=index, title=str(index), author=author)

    assert replica_models.AuthorRef.objects.count() == 1
    assert replica_models.Book.objects.count() == 2

    author.refresh_from_db()
    author.delete()

    assert replica_models.AuthorRef.objects.count() == 0
    assert replica_models.Book.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_sync_is_deleted():
    author = master_models.Author.objects.create(id=1, name='author')
    author.refresh_from_db()

    assert replica_models.AuthorRef.objects.count() == 1

    replica_models.AuthorRef.objects.all().delete()
    author.cqrs_sync()

    assert replica_models.AuthorRef.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_sync_exists(mocker):
    author = master_models.Author.objects.create(id=1, name='author')
    author.refresh_from_db()

    assert replica_models.AuthorRef.objects.count() == 1

    # We simulate transport error
    mocker.patch('dj_cqrs.controller.producer.produce')
    author.name = 'new'
    author.save()
    mocker.stopall()

    author.cqrs_sync()

    assert replica_models.AuthorRef.objects.count() == 1
    replica_author = replica_models.AuthorRef.objects.first()
    assert replica_author.cqrs_revision == 1
    assert replica_author.name == 'new'


@pytest.mark.django_db(transaction=True)
def test_sync_downgrade(mocker, caplog):
    author = master_models.Author.objects.create(id=1, name='author')
    author.name = 'new'
    author.save()

    assert replica_models.AuthorRef.objects.count() == 1
    replica_author = replica_models.AuthorRef.objects.first()
    assert replica_author.cqrs_revision == 1
    assert replica_author.name == 'new'

    mocker.patch('dj_cqrs.controller.producer.produce')
    author.delete()
    author = master_models.Author.objects.create(id=1, name='other')
    mocker.stopall()

    author.cqrs_sync()

    assert replica_models.AuthorRef.objects.count() == 1
    replica_author = replica_models.AuthorRef.objects.first()
    assert replica_author.cqrs_revision == 0
    assert replica_author.name == 'other'

    assert 'CQRS revision downgrade on sync: pk = 1, cqrs_revision = new 0 / existing 1 (author).' \
        in caplog.text
