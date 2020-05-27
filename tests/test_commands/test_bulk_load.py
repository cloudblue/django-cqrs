#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest
from django.core.management import CommandError, call_command
from django.utils.timezone import now
from tests.utils import db_error

from tests.dj_replica.models import AuthorRef


COMMAND_NAME = 'cqrs_bulk_load'
DUMPS_PATH = 'tests/test_commands/dumps/'


def test_no_input():
    with pytest.raises(CommandError):
        call_command(COMMAND_NAME)


def test_no_file():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '-i=__init__1.py')

    assert "File __init__1.py doesn't exist!" in str(e)


def test_empty_file():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '-i={}empty_file.dump'.format(DUMPS_PATH))

    assert "empty_file.dump is empty!" in str(e)


def test_no_cqrs_id():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '-i={}bad_cqrs_id.dump'.format(DUMPS_PATH))

    assert "Wrong CQRS ID: publisher!" in str(e)


@pytest.mark.django_db
def test_unparseable_line(capsys):
    call_command(COMMAND_NAME, '-i={}unparseable.dump'.format(DUMPS_PATH))
    assert AuthorRef.objects.count() == 0

    captured = capsys.readouterr()
    assert "Dump file can't be parsed: line 2!" in captured.err
    assert '0 instance(s) loaded.' in captured.err


@pytest.mark.django_db
def test_bad_master_data(capsys):
    call_command(COMMAND_NAME, '-i={}bad_master_data.dump'.format(DUMPS_PATH))
    assert AuthorRef.objects.count() == 1

    captured = capsys.readouterr()
    assert "Instance can't be saved: line 3!" in captured.err
    assert '1 instance(s) loaded.' in captured.err


@pytest.mark.django_db
def test_no_rows(capsys):
    AuthorRef.objects.create(id=1, name='1', cqrs_revision=0, cqrs_updated=now())

    call_command(COMMAND_NAME, '--input={}no_rows.dump'.format(DUMPS_PATH))
    assert AuthorRef.objects.count() == 1

    captured = capsys.readouterr()
    assert '0 instance(s) loaded.' in captured.err


@pytest.mark.django_db(transaction=True)
def test_loaded_correctly(capsys):
    AuthorRef.objects.create(id=1, name='1', cqrs_revision=0, cqrs_updated=now())

    call_command(COMMAND_NAME, '--input={}author.dump'.format(DUMPS_PATH))
    assert AuthorRef.objects.count() == 2

    captured = capsys.readouterr()
    assert '2 instance(s) loaded.' in captured.err


@pytest.mark.django_db
def test_delete_before_upload_ok(capsys):
    AuthorRef.objects.create(id=1, name='1', cqrs_revision=0, cqrs_updated=now())

    call_command(COMMAND_NAME, '--input={}no_rows.dump'.format(DUMPS_PATH), '--clear=true')
    assert AuthorRef.objects.count() == 0

    captured = capsys.readouterr()
    assert '0 instance(s) loaded.' in captured.err


@pytest.mark.django_db
def test_delete_operation_fails(mocker, ):
    mocker.patch('django.db.models.manager.BaseManager.all', side_effect=db_error)
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--input={}no_rows.dump'.format(DUMPS_PATH), '--clear=true')

    assert "Delete operation fails!" in str(e)


@pytest.mark.django_db
def test_unexpected_error(mocker, capsys):
    mocker.patch('tests.dj_replica.models.AuthorRef.cqrs_save', side_effect=db_error)
    call_command(COMMAND_NAME, '--input={}author.dump'.format(DUMPS_PATH))

    captured = capsys.readouterr()
    assert 'Unexpected error: line 2!' in captured.err
    assert 'Unexpected error: line 3!' in captured.err
    assert '0 instance(s) loaded.' in captured.err


@pytest.mark.django_db(transaction=True)
def test_loaded_correctly_batch(capsys):
    AuthorRef.objects.create(id=1, name='1', cqrs_revision=0, cqrs_updated=now())

    call_command(COMMAND_NAME, '--input={}author.dump'.format(DUMPS_PATH), '--batch=1')
    assert AuthorRef.objects.count() == 2

    captured = capsys.readouterr()
    assert '2 instance(s) loaded.' in captured.err
