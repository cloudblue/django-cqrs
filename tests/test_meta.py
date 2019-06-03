from __future__ import unicode_literals

import pytest

from dj_cqrs.mixins import _MetaUtils
from dj_cqrs.registries import MasterRegistry, ReplicaRegistry


@pytest.mark.django_db
def test_no_cqrs_id():
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRS_ID = None

        _MetaUtils.check_cqrs_id(Cls)

    assert str(e.value) == 'CQRS_ID must be set for every model, that uses CQRS.'


@pytest.mark.parametrize('registry', [MasterRegistry, ReplicaRegistry])
def test_duplicate_cqrs_id(registry):
    class Cls(object):
        CQRS_ID = 'basic'

    with pytest.raises(AssertionError) as e:
        registry.register_model(Cls)

    assert str(e.value) == "Two models can't have the same CQRS_ID: basic."
