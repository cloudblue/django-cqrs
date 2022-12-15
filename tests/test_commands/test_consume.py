#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from importlib import import_module, reload

import pytest
from django.core.management import CommandError, call_command

from dj_cqrs.management.commands.cqrs_consume import WorkersManager
from dj_cqrs.transport import current_transport


COMMAND_NAME = 'cqrs_consume'


@pytest.fixture
def reload_transport():
    reload(import_module('dj_cqrs.transport'))


def test_no_arguments(mocker, reload_transport):
    consume_mock = mocker.patch('tests.dj.transport.TransportStub.consume')

    call_command(COMMAND_NAME)

    consume_mock.assert_called_once_with()


def test_several_workers(reload_transport):
    call_command(COMMAND_NAME, '--workers=2')


def test_reload_flag(reload_transport):
    call_command(COMMAND_NAME, '--reload')


def test_workers_manager(reload_transport):
    manager = WorkersManager({'workers': 1}, current_transport, {})
    manager.start()
    manager.reload()


def test_one_worker_one_cqrs_id(mocker, reload_transport):
    consume_mock = mocker.patch('dj_cqrs.management.commands.cqrs_consume.WorkersManager.start')

    call_command(COMMAND_NAME, '--workers=1', '-cid=author')

    consume_mock.assert_called_once_with()


def test_several_cqrs_id(mocker, reload_transport):
    consume_mock = mocker.patch('tests.dj.transport.TransportStub.consume')

    call_command(COMMAND_NAME, cqrs_id=['author', 'basic', 'author', 'no_db'])

    consume_mock.assert_called_once_with(cqrs_ids={'author', 'basic', 'no_db'})


def test_wrong_cqrs_id(reload_transport):
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, cqrs_id=['author', 'random', 'no_db'])

    assert "Wrong CQRS ID: random!" in str(e)
