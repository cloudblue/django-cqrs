#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest

from dj_cqrs.constants import SignalType
from dj_cqrs.controller.consumer import route_signal_to_replica_model
from dj_cqrs.mixins import ReplicaMixin


def test_bad_model(caplog):
    route_signal_to_replica_model(SignalType.SAVE, 'invalid', {})
    assert 'No model with such CQRS_ID: invalid.' in caplog.text


def test_bad_signal(caplog):
    route_signal_to_replica_model('invalid', 'basic', {})
    assert 'Bad signal type "invalid" for CQRS_ID "basic".' in caplog.text


@pytest.mark.django_db
def test_save_model(mocker):
    cqrs_save_mock = mocker.patch.object(ReplicaMixin, 'cqrs_save')
    route_signal_to_replica_model(SignalType.SAVE, 'basic', {}, {})

    cqrs_save_mock.assert_called_once_with({}, previous_data={})


@pytest.mark.django_db
def test_delete_model(mocker):
    cqrs_delete_mock = mocker.patch.object(ReplicaMixin, 'cqrs_delete')
    route_signal_to_replica_model(SignalType.DELETE, 'basic', {'id': 1})

    cqrs_delete_mock.assert_called_once_with({'id': 1})
