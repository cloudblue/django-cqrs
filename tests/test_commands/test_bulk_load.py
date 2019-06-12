from __future__ import unicode_literals

import pytest
from django.core.management import CommandError, call_command
from django.utils.timezone import now

from tests.dj_replica.models import AuthorRef


COMMAND_NAME = 'cqrs_bulk_load'
DUMPS_PATH = 'tests/test_commands/dumps/'


def test_no_input():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME)

    assert 'Error: argument --input/-i is required' in str(e)


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
def test_unparseable_line():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '-i={}unparseable.dump'.format(DUMPS_PATH))

    assert "Dump file can't be parsed: line 2!" in str(e)


@pytest.mark.django_db
def test_bad_master_data():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '-i={}bad_master_data.dump'.format(DUMPS_PATH))

    assert "Instance can't be saved: line 3!" in str(e)


@pytest.mark.django_db
def test_no_rows(capsys):
    AuthorRef.objects.create(id=1, name='1', cqrs_revision=0, cqrs_updated=now())

    call_command(COMMAND_NAME, '--input={}no_rows.dump'.format(DUMPS_PATH))
    assert AuthorRef.objects.count() == 0

    captured = capsys.readouterr()
    assert 'Done! 0 instance(s) saved.' in captured.out


@pytest.mark.django_db(transaction=True)
def test_loaded_correctly(capsys):
    AuthorRef.objects.create(id=1, name='1', cqrs_revision=0, cqrs_updated=now())

    call_command(COMMAND_NAME, '--input={}author.dump'.format(DUMPS_PATH))
    assert AuthorRef.objects.count() == 2

    captured = capsys.readouterr()
    assert 'Done! 2 instance(s) saved.' in captured.out
