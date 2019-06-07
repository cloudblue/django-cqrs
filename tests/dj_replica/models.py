from __future__ import unicode_literals

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
