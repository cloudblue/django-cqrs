from __future__ import unicode_literals

import pytest
from uuid import uuid4
from django.utils.timezone import now

from dj_cqrs.mixins import _MasterMeta
from tests.dj_master import models


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
        'int_field': 1, 'bool_field': False, 'char_field': 'str',
        'date_field': None, 'datetime_field': dt, 'float_field': 1.23,
        'url_field': 'http://example.com', 'uuid_field': uid,
    }


def test_model_to_cqrs_dict_all_fields():
    m = models.AllFieldsModel(char_field='str')
    assert m.model_to_cqrs_dict() == {'id': None, 'int_field': None, 'char_field': 'str'}


def test_model_to_cqrs_dict_chosen_fields():
    m = models.ChosenFieldsModel(float_field=1.23)
    assert m.model_to_cqrs_dict() == {'char_field': None}


@pytest.mark.django_db
def test_model_to_cqrs_dict_auto_fields():
    m = models.AutoFieldsModel()
    assert m.model_to_cqrs_dict() == {'id': None, 'created': None, 'updated': None}

    m.save()
    cqrs_dct = m.model_to_cqrs_dict()
    for key in ('id', 'created', 'updated'):
        assert cqrs_dct[key] is not None


@pytest.mark.django_db
def test_no_cqrs_id():
    with pytest.raises(AssertionError) as e:
        class Cls(object):
            CQRS_ID = None
        _MasterMeta.check_cqrs_id(Cls, 'cls')
    assert str(e.value) == 'CQRS_ID must be set for every model, that uses CQRS.'
