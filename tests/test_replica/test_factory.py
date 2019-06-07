from __future__ import unicode_literals

from dj_cqrs.constants import SignalType
from dj_cqrs.factories import ReplicaFactory
from dj_cqrs.mixins import ReplicaMixin


def test_bad_model(caplog):
    ReplicaFactory.factory(SignalType.SAVE, 'invalid', {})
    assert 'No model with such CQRS_ID: invalid.' in caplog.text


def test_bad_signal(caplog):
    ReplicaFactory.factory('invalid', 'basic', {})
    assert 'Bad signal type "invalid" for CQRS_ID "basic".' in caplog.text


def test_save_model(mocker):
    cqrs_save_mock = mocker.patch.object(ReplicaMixin, 'cqrs_save')
    ReplicaFactory.factory(SignalType.SAVE, 'basic', {})

    cqrs_save_mock.assert_called_once_with({})


def test_delete_model(mocker):
    cqrs_delete_mock = mocker.patch.object(ReplicaMixin, 'cqrs_delete')
    ReplicaFactory.factory(SignalType.DELETE, 'basic', {'id': 1})

    cqrs_delete_mock.assert_called_once_with({'id': 1})
