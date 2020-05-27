#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import sys
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command
from django.utils.timezone import now

from tests.dj_master.models import Author
from tests.dj_replica.models import AuthorRef


COMMAND_NAME = 'cqrs_diff_replica'


def test_bad_cqrs_id(mocker):
    mocker.patch.object(sys, 'stdin', StringIO('invalid,datetime\n'))

    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME)

    assert 'Wrong CQRS ID: invalid!' in str(e)


@pytest.mark.django_db
def test_no_rows(mocker, capsys):
    mocker.patch.object(sys, 'stdin', StringIO('author,datetime\n'))
    call_command(COMMAND_NAME)

    captured = capsys.readouterr()
    assert not captured.err
    assert 'author,datetime,replica\n' == captured.out


def master_replica_pipe(capsys, mocker, *args):
    call_command('cqrs_diff_master', '--cqrs-id=author', *args)
    captured = capsys.readouterr()
    mocker.patch.object(sys, 'stdin', StringIO(captured.out))
    call_command(COMMAND_NAME)
    return capsys.readouterr()


@pytest.mark.django_db
def test_first_row(capsys, mocker):
    Author.objects.create(name='author', id=1)

    captured = master_replica_pipe(capsys, mocker)

    first_row = captured.out.split('\n')[0]
    assert '{},'.format(Author.CQRS_ID) in first_row
    assert settings.CQRS['queue'] in first_row


@pytest.mark.django_db
def test_all_synced(capsys, mocker):
    mocker.patch('dj_cqrs.controller.producer.produce')

    Author.objects.create(id=1, name='name')
    AuthorRef.objects.create(id=1, name='name', cqrs_revision=0, cqrs_updated=now())

    captured = master_replica_pipe(capsys, mocker)
    assert not captured.err


@pytest.mark.django_db
def test_sync_for_all(mocker, capsys):
    for i in range(3):
        Author.objects.create(name=str(i), id=i)

    captured = master_replica_pipe(capsys, mocker)
    for err_text in ('PK to resync', '0', '1', '2'):
        assert err_text in captured.err

    second_row = captured.out.split('\n')[1]
    assert '[0,1,2]' in second_row


@pytest.mark.django_db
def test_partial_sync(mocker, capsys):
    mocker.patch('dj_cqrs.controller.producer.produce')

    Author.objects.create(id=1, name='name')
    AuthorRef.objects.create(id=1, name='name', cqrs_revision=0, cqrs_updated=now())
    Author.objects.create(id=2, name='2')

    captured = master_replica_pipe(capsys, mocker)
    assert 'PK to resync' in captured.err
    assert '2' in captured.err

    second_row = captured.out.split('\n')[1]
    assert '[2]' in second_row


@pytest.mark.django_db
def test_sync_batch(mocker, capsys):
    mocker.patch('dj_cqrs.controller.producer.produce')

    for i in range(3):
        Author.objects.create(id=i, name=str(i))
    AuthorRef.objects.create(id=1, name='name', cqrs_revision=0, cqrs_updated=now())

    captured = master_replica_pipe(capsys, mocker, '--batch=1')
    for err_text in ('PK to resync', '0', '2'):
        assert err_text in captured.err

    second_row = captured.out.split('\n')[1]
    assert '[0]' in second_row

    third_row = captured.out.split('\n')[2]
    assert '[2]' in third_row
