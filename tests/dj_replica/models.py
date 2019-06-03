from __future__ import unicode_literals

from django.db import models

from dj_cqrs.mixins import ReplicaMixin


class BasicFieldsModelRef(ReplicaMixin, models.Model):
    CQRS_ID = 'basic'

    int_field = models.IntegerField(primary_key=True)
    bool_field = models.NullBooleanField()
    char_field = models.CharField(max_length=200, null=True)
    date_field = models.DateField(null=True)
    datetime_field = models.DateTimeField(null=True)
    float_field = models.FloatField(null=True)
    url_field = models.URLField(null=True)
    uuid_field = models.UUIDField(null=True)


class BadTypeModelRef(ReplicaMixin, models.Model):
    CQRS_ID = 'basic_1'

    int_field = models.IntegerField(primary_key=True)
    date_field = models.NullBooleanField()


class BadFieldModelRef(ReplicaMixin, models.Model):
    CQRS_ID = 'basic_2'

    int_field = models.IntegerField(primary_key=True)
    invalid_field = models.IntegerField()


class MappedFieldsModelRef(ReplicaMixin, models.Model):
    CQRS_ID = 'basic_3'
    CQRS_MAPPER = {
        'int_field': 'id',
        'char_field': 'name',
    }

    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=200)
