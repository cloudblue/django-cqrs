#  Copyright © 2023 Ingram Micro Inc. All rights reserved.

import sys
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.utils.timezone import now

from tests.dj_master.models import Author
from tests.dj_replica.models import AuthorRef


COMMAND_NAME = 'cqrs_deleted_sync_replica'


def test_bad_cqrs_id(mocker):
    mocker.patch.object(sys, 'stdin', StringIO('invalid,datetime\n'))

    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME)

    assert 'Wrong CQRS ID: invalid!' in str(e)


def diff_pipe(capsys, mocker, *args):
    call_command('cqrs_deleted_diff_replica', '--cqrs-id=author', *args)
    captured = capsys.readouterr()

    mocker.patch.object(sys, 'stdin', StringIO(captured.out))
    call_command('cqrs_deleted_diff_master')
    captured = capsys.readouterr()
    mocker.stopall()

    mocker.patch.object(sys, 'stdin', StringIO(captured.out))
    call_command(COMMAND_NAME)


@pytest.mark.django_db
def test_all_synced(capsys, mocker):
    mocker.patch('dj_cqrs.controller.producer.produce')

    Author.objects.create(id=1, name='name')
    AuthorRef.objects.create(id=1, name='name', cqrs_revision=0, cqrs_updated=now())

    diff_pipe(capsys, mocker)

    assert AuthorRef.objects.count() == 1


@pytest.mark.django_db
def test_sync_for_all(mocker, capsys):
    AuthorRef.objects.create(id=1, name='name', cqrs_revision=0, cqrs_updated=now())

    diff_pipe(capsys, mocker)

    assert not AuthorRef.objects.exists()


@pytest.mark.django_db
def test_partial_sync(mocker, capsys):
    mocker.patch('dj_cqrs.controller.producer.produce')

    Author.objects.create(id=1, name='name')
    AuthorRef.objects.create(id=1, name='name', cqrs_revision=0, cqrs_updated=now())
    AuthorRef.objects.create(id=2, name='name', cqrs_revision=0, cqrs_updated=now())

    diff_pipe(capsys, mocker)

    assert list(AuthorRef.objects.all()) == [AuthorRef(id=1)]


@pytest.mark.django_db
def test_sync_batch(mocker, capsys):
    mocker.patch('dj_cqrs.controller.producer.produce')

    for i in range(3):
        AuthorRef.objects.create(id=i, name='name', cqrs_revision=0, cqrs_updated=now())
    Author.objects.create(id=2, name='name')

    diff_pipe(capsys, mocker, '--batch=1')
    assert list(AuthorRef.objects.all()) == [AuthorRef(id=2)]
