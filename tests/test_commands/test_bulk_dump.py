#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import ujson

import pytest
from django.core.management import CommandError, call_command
from django.db import transaction
from tests.utils import db_error

from tests.dj_master.models import Author, Publisher
from tests.test_commands.utils import remove_file

COMMAND_NAME = 'cqrs_bulk_dump'


def test_no_cqrs_id():
    with pytest.raises(CommandError):
        call_command(COMMAND_NAME)


def test_bad_cqrs_id():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs-id=invalid')

    assert 'Wrong CQRS ID: invalid!' in str(e)


def test_output_file_exists():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs-id=author', '-o=setup.py')

    assert 'File setup.py exists!' in str(e)


@pytest.mark.django_db
def test_dumps_no_rows(capsys):
    remove_file('author.dump')

    call_command(COMMAND_NAME, '--cqrs-id=author')

    with open('author.dump', 'r') as f:
        lines = f.readlines()
        assert len(lines) == 1
        assert lines[0] == 'author'

    captured = capsys.readouterr()
    assert 'Done!\n0 instance(s) saved.\n0 instance(s) processed.' in captured.err


@pytest.mark.django_db
def tests_dumps_several_rows(capsys):
    remove_file('author.dump')

    Author.objects.create(id=2, name='2')

    with transaction.atomic():
        publisher = Publisher.objects.create(id=1, name='publisher')
        author = Author.objects.create(id=1, name='1', publisher=publisher)

    call_command(COMMAND_NAME, '--cqrs-id=author')

    with open('author.dump', 'r') as f:
        lines = f.readlines()
        assert len(lines) == 3
        assert lines[0].strip() == 'author'

        line_with_publisher = next(ln for ln in lines[1:] if '"name":"publisher"' in ln)
        assert author.to_cqrs_dict() == ujson.loads(line_with_publisher)

    captured = capsys.readouterr()
    assert 'Done!\n2 instance(s) saved.\n2 instance(s) processed.' in captured.err


@pytest.mark.django_db
def tests_dumps_more_than_batch(capsys):
    remove_file('author.dump')

    Author.objects.bulk_create(
        (Author(id=index, name='n') for index in range(1, 150)),
    )

    call_command(COMMAND_NAME, '--cqrs-id=author')

    with open('author.dump', 'r') as f:
        lines = f.readlines()
        assert len(lines) == 150

    captured = capsys.readouterr()
    assert 'Done!\n149 instance(s) saved.\n149 instance(s) processed.' in captured.err


@pytest.mark.django_db
def test_error(capsys, mocker):
    remove_file('author.dump')
    Author.objects.create(id=2, name='2')

    mocker.patch('tests.dj_master.models.Author.to_cqrs_dict', side_effect=db_error)
    call_command(COMMAND_NAME, '--cqrs-id=author')

    captured = capsys.readouterr()
    assert 'Dump record failed for pk=2' in captured.err
    assert '1 instance(s) processed.' in captured.err
    assert '0 instance(s) saved.' in captured.err


@pytest.mark.django_db
def test_progress(capsys):
    remove_file('author.dump')

    Author.objects.create(id=2, name='2')
    call_command(COMMAND_NAME, '--cqrs-id=author', '--progress')

    captured = capsys.readouterr()
    assert 'Processing 1 records with batch size 10000' in captured.err
    assert '1 of 1 processed - 100% with rate' in captured.err
