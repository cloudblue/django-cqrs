from __future__ import unicode_literals

from django.db import models

from dj_cqrs.mixins import MasterMixin


class BasicFieldsModel(MasterMixin, models.Model):
    CQRS_ID = 'basic'

    int_field = models.IntegerField(primary_key=True)
    bool_field = models.NullBooleanField()
    char_field = models.CharField(max_length=200, null=True)
    date_field = models.DateField(null=True)
    datetime_field = models.DateTimeField(null=True)
    float_field = models.FloatField(null=True)
    url_field = models.URLField(null=True)
    uuid_field = models.UUIDField(null=True)


class AllFieldsModel(MasterMixin, models.Model):
    CQRS_FIELDS = '__all__'
    CQRS_ID = 'all'

    int_field = models.IntegerField(null=True)
    char_field = models.CharField(max_length=200, null=True)


class ChosenFieldsModel(MasterMixin, models.Model):
    CQRS_FIELDS = ('char_field',)
    CQRS_ID = 'chosen'

    float_field = models.IntegerField(null=True)
    char_field = models.CharField(max_length=200, null=True)


class AutoFieldsModel(MasterMixin, models.Model):
    CQRS_ID = 'auto'

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
