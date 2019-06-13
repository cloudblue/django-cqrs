from __future__ import unicode_literals


import pytest
from django.core.management import CommandError, call_command

from dj_cqrs.constants import SignalType
from tests.dj_master.models import Author

COMMAND_NAME = 'cqrs_sync'


def test_no_cqrs_id():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME)

    assert 'Error: argument --cqrs_id/-cid is required' in str(e)


def test_bad_cqrs_id():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs_id=invalid')

    assert 'Wrong CQRS ID: invalid!' in str(e)


def test_empty_filter_arg(capsys):
    call_command(COMMAND_NAME, '--cqrs_id=author')

    captured = capsys.readouterr()
    assert 'No objects found for filter!' in captured.out


def test_unparseable_filter():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs_id=author', '-f={arg}')

    assert 'Bad filter kwargs!' in str(e)


def test_non_kwargs_filter():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs_id=author', '-f=[1]')

    assert 'Bad filter kwargs!' in str(e)


def test_bad_kwargs_filter():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs_id=author', '-f={"field": "value"}')

    assert 'Bad filter kwargs! Cannot resolve keyword' in str(e)


@pytest.mark.django_db
def test_empty_filter(capsys):
    call_command(COMMAND_NAME, '--cqrs_id=author', '-f={"id": 1}')

    captured = capsys.readouterr()
    assert 'No objects found for filter!' in captured.out


@pytest.mark.django_db(transaction=True)
def test_no_queue(mocker, capsys):
    Author.objects.create(id=1, name='author')

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    call_command(COMMAND_NAME, '--cqrs_id=author', '-f={"id": 1}')

    publisher_mock.assert_called_once()
    payload = publisher_mock.call_args[0][0]
    assert payload.queue is None
    assert payload.signal_type is SignalType.SYNC

    captured = capsys.readouterr()
    assert 'Done! 1 instance(s) synced.' in captured.out


@pytest.mark.django_db(transaction=True)
def test_queue_is_set(mocker, capsys):
    Author.objects.create(id=1, name='author')

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    call_command(COMMAND_NAME, '--cqrs_id=author', '-f={"id": 1}', '--queue=replica')

    publisher_mock.assert_called_once()
    payload = publisher_mock.call_args[0][0]
    assert payload.queue == 'replica'
    assert payload.signal_type is SignalType.SYNC

    captured = capsys.readouterr()
    assert 'Done! 1 instance(s) synced.' in captured.out


@pytest.mark.django_db(transaction=True)
def test_several_synced(mocker, capsys):
    for i in range(1, 3):
        Author.objects.create(id=i, name='author')

    publisher_mock = mocker.patch('dj_cqrs.controller.producer.produce')
    call_command(COMMAND_NAME, '--cqrs_id=author', '-f={"id__in": [1, 2]}')

    assert publisher_mock.call_count == 2

    captured = capsys.readouterr()
    assert 'Done! 2 instance(s) synced.' in captured.out
