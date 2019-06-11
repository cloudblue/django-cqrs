from __future__ import unicode_literals

import os
import ujson

import pytest
from django.core.management import CommandError, call_command
from django.db import transaction

from tests.dj_master.models import Author, Publisher


COMMAND_NAME = 'cqrs_bulk_dump'


def test_no_cqrs_id():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME)

    assert 'Error: argument --cqrs_id/-cid is required' in str(e)


def test_bad_cqrs_id():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs_id=invalid')

    assert 'Wrong CQRS ID: invalid!' in str(e)


def test_output_file_exists():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs_id=author', '-o=setup.py')

    assert 'File setup.py exists!' in str(e)


def remove_file(path):
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.mark.django_db
def test_dumps_no_rows(capsys):
    remove_file('author.dump')

    call_command(COMMAND_NAME, '--cqrs_id=author')

    with open('author.dump', 'r') as f:
        lines = f.readlines()
        assert len(lines) == 1
        assert lines[0] == 'author'

    captured = capsys.readouterr()
    assert 'Done! 0 instance(s) saved.' in captured.out


@pytest.mark.django_db
def tests_dumps_several_rows(capsys):
    remove_file('author.dump')

    Author.objects.create(id=2, name='2')

    with transaction.atomic():
        publisher = Publisher.objects.create(id=1, name='publisher')
        author = Author.objects.create(id=1, name='1', publisher=publisher)

    call_command(COMMAND_NAME, '--cqrs_id=author')

    with open('author.dump', 'r') as f:
        lines = f.readlines()
        assert len(lines) == 3
        assert lines[0].strip() == 'author'

        line_with_publisher = next(l for l in lines[1:] if '"name":"publisher"' in l)
        assert author.to_cqrs_dict() == ujson.loads(line_with_publisher)

    captured = capsys.readouterr()
    assert 'Done! 2 instance(s) saved.' in captured.out


@pytest.mark.django_db
def tests_dumps_more_than_batch(capsys):
    remove_file('author.dump')

    Author.objects.bulk_create(
        Author(id=index, name='n') for index in range(1, 150),
    )

    call_command(COMMAND_NAME, '--cqrs_id=author')

    with open('author.dump', 'r') as f:
        lines = f.readlines()
        assert len(lines) == 150

    captured = capsys.readouterr()
    assert 'Done! 149 instance(s) saved.' in captured.out
