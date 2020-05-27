#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import sys
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.utils.timezone import now

from dj_cqrs.constants import NO_QUEUE
from dj_cqrs.management.commands import cqrs_sync
from tests.dj_master.models import Author
from tests.dj_replica.models import AuthorRef


COMMAND_NAME = 'cqrs_diff_sync'


def test_bad_cqrs_id(mocker):
    mocker.patch.object(sys, 'stdin', StringIO('invalid,datetime,replica\n'))

    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME)

    assert 'Wrong CQRS ID: invalid!' in str(e)


def diff_pipe(capsys, mocker, *args):
    call_command('cqrs_diff_master', '--cqrs-id=author', *args)
    captured = capsys.readouterr()

    mocker.patch.object(sys, 'stdin', StringIO(captured.out))
    call_command('cqrs_diff_replica')
    captured = capsys.readouterr()
    mocker.stopall()

    sync_mock = mocker.patch.object(cqrs_sync.Command, 'handle')
    mocker.patch.object(sys, 'stdin', StringIO(captured.out))
    call_command(COMMAND_NAME)

    return sync_mock


@pytest.mark.django_db
def test_all_synced(capsys, mocker):
    mocker.patch('dj_cqrs.controller.producer.produce')

    Author.objects.create(id=1, name='name')
    AuthorRef.objects.create(id=1, name='name', cqrs_revision=0, cqrs_updated=now())

    sync_mock = diff_pipe(capsys, mocker)
    sync_mock.assert_not_called()


@pytest.mark.django_db
def test_sync_for_all(mocker, capsys):
    mocker.patch('dj_cqrs.controller.producer.produce')
    Author.objects.create(name='a', id=1)

    sync_mock = diff_pipe(capsys, mocker)
    sync_mock.assert_called_once_with(
        **{'cqrs_id': 'author', 'filter': '{"id__in": [1]}', 'queue': 'replica'},
    )


@pytest.mark.django_db
def test_partial_sync(mocker, capsys):
    mocker.patch('dj_cqrs.controller.producer.produce')

    Author.objects.create(id=1, name='name')
    AuthorRef.objects.create(id=1, name='name', cqrs_revision=0, cqrs_updated=now())
    Author.objects.create(id=2, name='2')

    sync_mock = diff_pipe(capsys, mocker)
    sync_mock.assert_called_once_with(
        **{'cqrs_id': 'author', 'filter': '{"id__in": [2]}', 'queue': 'replica'},
    )


@pytest.mark.django_db
def test_sync_batch(mocker, capsys):
    mocker.patch('dj_cqrs.controller.producer.produce')

    for i in range(3):
        Author.objects.create(id=i, name=str(i))
    AuthorRef.objects.create(id=1, name='name', cqrs_revision=0, cqrs_updated=now())

    sync_mock = diff_pipe(capsys, mocker, '--batch=1')
    assert sync_mock.call_count == 2


@pytest.mark.django_db
def test_sync_no_queue(mocker):
    sync_mock = mocker.patch.object(cqrs_sync.Command, 'handle')
    mocker.patch.object(sys, 'stdin', StringIO('author,dt,{}\n[1]\n'.format(NO_QUEUE)))
    call_command(COMMAND_NAME)

    sync_mock.assert_called_once_with(**{'cqrs_id': 'author', 'filter': '{"id__in": [1]}'})
