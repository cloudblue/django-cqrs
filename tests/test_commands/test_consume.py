#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import threading
from importlib import import_module, reload
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from dj_cqrs.management.commands.cqrs_consume import WorkersManager, consume


COMMAND_NAME = 'cqrs_consume'


@pytest.fixture
def reload_transport():
    reload(import_module('dj_cqrs.transport'))


def test_no_arguments(mocker, reload_transport):
    mocked_worker = mocker.patch('dj_cqrs.management.commands.cqrs_consume.WorkersManager')

    call_command(COMMAND_NAME)

    mocked_worker.assert_called_once_with(
        consume_kwargs={},
        workers=1,
        reload=False,
        ignore_paths=None,
        sigint_timeout=5,
        sigkill_timeout=1,
    )


def test_with_arguments(mocker, reload_transport):
    mocked_worker = mocker.patch('dj_cqrs.management.commands.cqrs_consume.WorkersManager')
    mocker.patch(
        'dj_cqrs.management.commands.cqrs_consume.Path',
        side_effect=[
            mocker.MagicMock(resolve=mocker.MagicMock(return_value='/path1')),
            mocker.MagicMock(resolve=mocker.MagicMock(return_value='/path2')),
        ],
    )

    call_command(COMMAND_NAME, '--workers=2', '-r', '-cid=author', '--ignore-paths=path1,path2')
    mocked_worker.assert_called_once_with(
        consume_kwargs={'cqrs_ids': {'author'}},
        workers=2,
        reload=True,
        ignore_paths=['/path1', '/path2'],
        sigint_timeout=5,
        sigkill_timeout=1,
    )


def test_several_cqrs_id(mocker, reload_transport):
    mocked_worker = mocker.patch('dj_cqrs.management.commands.cqrs_consume.WorkersManager')

    call_command(COMMAND_NAME, cqrs_id=['author', 'basic', 'author', 'no_db'])

    mocked_worker.assert_called_once_with(
        consume_kwargs={'cqrs_ids': {'author', 'basic', 'no_db'}},
        workers=1,
        reload=False,
        ignore_paths=None,
        sigint_timeout=5,
        sigkill_timeout=1,
    )


def test_wrong_cqrs_id(reload_transport):
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, cqrs_id=['author', 'random', 'no_db'])

    assert "Wrong CQRS ID: random!" in str(e)


def test_worker_manager_constructor_with_reload(mocker):
    mocked_flt_instance = mocker.MagicMock()
    mocked_pyfilter = mocker.patch(
        'dj_cqrs.management.commands.cqrs_consume.PythonFilter',
        return_value=mocked_flt_instance,
    )
    mocked_watch = mocker.patch('dj_cqrs.management.commands.cqrs_consume.watch')

    worker = WorkersManager(
        {},
        reload=True,
        sigint_timeout=10,
    )

    assert worker.workers == 1
    assert worker.reload is True
    assert worker.sigint_timeout == 10
    assert worker.sigkill_timeout == 1
    assert isinstance(worker.stop_event, threading.Event)

    mocked_pyfilter.assert_called_once_with(ignore_paths=None)
    assert worker.watch_filter == mocked_flt_instance
    mocked_watch.assert_called_once_with(
        Path.cwd(),
        watch_filter=mocked_flt_instance,
        stop_event=worker.stop_event,
        yield_on_timeout=True,
    )


def test_worker_manager_run_no_reload(mocker):
    mocked_start_process = mocker.patch('dj_cqrs.management.commands.cqrs_consume.start_process')

    worker = WorkersManager(
        {'cqrs_ids': {'author', 'basic', 'no_db'}},
        workers=2,
    )
    worker.stop_event.wait = mocker.MagicMock()

    worker.run()

    mocked_start_process.assert_called()


def test_worker_manager_run_with_reload(mocker):
    mocker.patch.object(
        WorkersManager,
        '__next__',
        side_effect=[[Path.cwd() / Path('file1.py')], None],
    )
    mocked_start_process = mocker.patch('dj_cqrs.management.commands.cqrs_consume.start_process')

    worker = WorkersManager(
        {'cqrs_ids': {'author', 'basic', 'no_db'}},
        reload=True,
    )
    worker.stop_event.wait = mocker.MagicMock()

    worker.run()

    mocked_start_process.assert_called()


def test_worker_manager_handle_signal():
    worker = WorkersManager({})
    worker.handle_signal()

    assert worker.stop_event.is_set()


def test_worker_manager_iterator():
    worker = WorkersManager({})

    worker.watcher = iter([[(None, '/file1.py')], None])

    expected_result = [[Path('/file1.py')], None]
    result = []

    for file in worker:
        result.append(file)

    assert result == expected_result


def test_consume(mocker):
    mocked_setup = mocker.patch('django.setup')
    mocked_consume = mocker.patch(
        'dj_cqrs.transport.current_transport.consume',
    )

    consume_kwargs = {'cqrs_ids': {'author', 'basic', 'no_db'}}
    consume(**consume_kwargs)

    mocked_setup.assert_called_once()
    mocked_consume.assert_called_once_with(**consume_kwargs)
