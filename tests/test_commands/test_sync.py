#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest
from django.core.management import CommandError, call_command
from tests.utils import db_error

from dj_cqrs.constants import SignalType
from tests.dj_master.models import Author

COMMAND_NAME = 'cqrs_sync'


def test_no_cqrs_id():
    with pytest.raises(CommandError):
        call_command(COMMAND_NAME)


def test_bad_cqrs_id():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs-id=invalid')

    assert 'Wrong CQRS ID: invalid!' in str(e)


def test_empty_filter_arg(capsys):
    call_command(COMMAND_NAME, '--cqrs-id=author')

    captured = capsys.readouterr()
    assert 'No objects found for filter!' in captured.out


def test_unparseable_filter():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs-id=author', '-f={arg}')

    assert 'Bad filter kwargs!' in str(e)


def test_non_kwargs_filter():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs-id=author', '-f=[1]')

    assert 'Bad filter kwargs!' in str(e)


def test_bad_kwargs_filter():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs-id=author', '-f={"field": "value"}')

    assert 'Bad filter kwargs! Cannot resolve keyword' in str(e)


@pytest.mark.django_db
def test_empty_filter(capsys):
    call_command(COMMAND_NAME, '--cqrs-id=author', '-f={"id": 1}')

    captured = capsys.readouterr()
    assert 'No objects found for filter!' in captured.out


@pytest.mark.django_db(transaction=True)
def test_no_queue(mocker, capsys):
    Author.objects.create(id=1, name='author')

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    call_command(COMMAND_NAME, '--cqrs-id=author', '-f={"id": 1}')

    publisher_mock.assert_called_once()
    payload = publisher_mock.call_args[0][0]
    assert payload.queue is None
    assert payload.signal_type is SignalType.SYNC

    captured = capsys.readouterr()
    assert 'Done!\n1 instance(s) synced.\n1 instance(s) processed.' in captured.out


@pytest.mark.django_db(transaction=True)
def test_queue_is_set(mocker, capsys):
    Author.objects.create(id=1, name='author')

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    call_command(COMMAND_NAME, '--cqrs-id=author', '-f={"id": 1}', '--queue=replica')

    publisher_mock.assert_called_once()
    payload = publisher_mock.call_args[0][0]
    assert payload.queue == 'replica'
    assert payload.signal_type is SignalType.SYNC

    captured = capsys.readouterr()
    assert 'Done!\n1 instance(s) synced.\n1 instance(s) processed.' in captured.out


@pytest.mark.django_db(transaction=True)
def test_several_synced(mocker, capsys):
    for i in range(1, 3):
        Author.objects.create(id=i, name='author')

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    call_command(COMMAND_NAME, '--cqrs-id=author', '-f={"id__in": [1, 2]}')

    assert publisher_mock.call_count == 2

    captured = capsys.readouterr()
    assert 'Done!\n2 instance(s) synced.\n2 instance(s) processed.' in captured.out


@pytest.mark.django_db
def test_error(capsys, mocker):
    Author.objects.create(id=2, name='2')

    mocker.patch('tests.dj_master.models.Author.cqrs_sync', side_effect=db_error)
    call_command(COMMAND_NAME, '--cqrs-id=author', '-f={}')

    captured = capsys.readouterr()
    assert 'Sync record failed for pk=2' in captured.out
    assert '1 instance(s) processed.' in captured.out
    assert '0 instance(s) synced.' in captured.out


@pytest.mark.django_db
def test_progress(capsys):
    Author.objects.create(id=2, name='2')
    call_command(COMMAND_NAME, '--cqrs-id=author', '--progress', '-f={}', '--batch=2')

    captured = capsys.readouterr()
    assert 'Processing 1 records with batch size 2' in captured.out
    assert '1 of 1 processed - 100% with rate' in captured.out
