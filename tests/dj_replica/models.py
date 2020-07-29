#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

from django.db import models

from dj_cqrs.mixins import ReplicaMixin


class BasicFieldsModelRef(ReplicaMixin, models.Model):
    CQRS_ID = 'basic'

    int_field = models.IntegerField(primary_key=True)
    char_field = models.CharField(max_length=200)

    bool_field = models.NullBooleanField()
    date_field = models.DateField(null=True)
    datetime_field = models.DateTimeField(null=True)
    float_field = models.FloatField(null=True)
    url_field = models.URLField(null=True)
    uuid_field = models.UUIDField(null=True)


class BadTypeModelRef(ReplicaMixin, models.Model):
    CQRS_ID = 'basic_1'

    int_field = models.IntegerField(primary_key=True)
    datetime_field = models.NullBooleanField()


class MappedFieldsModelRef(ReplicaMixin, models.Model):
    CQRS_ID = 'basic_2'
    CQRS_MAPPING = {
        'int_field': 'id',
        'char_field': 'name',
    }

    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=200)


class BadMappingModelRef(ReplicaMixin, models.Model):
    CQRS_ID = 'basic_3'
    CQRS_MAPPING = {
        'int_field': 'id',
        'invalid_field': 'name',
    }

    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=200)


class Event(models.Model):
    pid = models.IntegerField()
    cqrs_id = models.CharField(max_length=20)
    cqrs_revision = models.IntegerField()

    time = models.DateTimeField(auto_now_add=True)


class Publisher(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=20)


class AuthorRef(ReplicaMixin, models.Model):
    CQRS_ID = 'author'
    CQRS_CUSTOM_SERIALIZATION = True

    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=20)

    publisher = models.ForeignKey(Publisher, null=True, on_delete=models.CASCADE)

    @classmethod
    def cqrs_create(cls, sync, mapped_data, previous_data=None):
        publisher_data, publisher = mapped_data.pop('publisher', None), None
        if publisher_data:
            publisher, _ = Publisher.objects.get_or_create(**publisher_data)

        books_data = mapped_data.pop('books', [])
        author = cls.objects.create(publisher=publisher, **mapped_data)

        Book.objects.bulk_create(Book(author=author, **book_data) for book_data in books_data)
        return author

    def cqrs_update(self, sync, mapped_data, previous_data=None):
        # It's just an example, that doesn't make sense in real cases
        publisher_data, publisher = mapped_data.pop('publisher', None), None
        if publisher_data:
            publisher, _ = Publisher.objects.get_or_create(**publisher_data)

        self.publisher = publisher
        self.name = mapped_data.get('name', self.name)
        self.cqrs_revision = mapped_data['cqrs_revision']
        self.cqrs_updated = mapped_data['cqrs_updated']
        self.save()

        return self


class Book(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=20)

    author = models.ForeignKey(AuthorRef, on_delete=models.CASCADE)
