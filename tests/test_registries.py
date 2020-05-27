#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest

from dj_cqrs.registries import MasterRegistry, ReplicaRegistry
from tests.dj_master import models as master_models
from tests.dj_replica import models as replica_models


@pytest.mark.parametrize('registry', [MasterRegistry, ReplicaRegistry])
def test_duplicate_cqrs_id(registry):
    class Cls(object):
        CQRS_ID = 'basic'

    with pytest.raises(AssertionError) as e:
        registry.register_model(Cls)

    assert str(e.value) == "Two models can't have the same CQRS_ID: basic."


@pytest.mark.parametrize('model,registry', (
    (master_models.SimplestModel, MasterRegistry),
    (master_models.AutoFieldsModel, MasterRegistry),
    (replica_models.BasicFieldsModelRef, ReplicaRegistry),
    (replica_models.BadTypeModelRef, ReplicaRegistry),
))
def test_models_are_registered(model, registry):
    assert registry.models[model.CQRS_ID] == model
    assert registry.get_model_by_cqrs_id(model.CQRS_ID) == model


def test_get_model_by_cqrs_id_no_id(caplog):
    assert ReplicaRegistry.get_model_by_cqrs_id('invalid') is None
    assert 'No model with such CQRS_ID: invalid.' in caplog.text


def test_no_cqrs_queue(settings):
    settings.CQRS.update({'queue': None})

    with pytest.raises(AssertionError) as e:
        ReplicaRegistry.register_model(replica_models.MappedFieldsModelRef)

    assert str(e.value) == 'CQRS queue must be set for the service, that has replica models.'
