#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import ujson

import pytest
from django.core.management import CommandError, call_command

from tests.dj_master.models import Author


COMMAND_NAME = 'cqrs_diff_master'


def test_no_cqrs_id():
    with pytest.raises(CommandError):
        call_command(COMMAND_NAME)


def test_bad_cqrs_id():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs-id=invalid')

    assert 'Wrong CQRS ID: invalid!' in str(e)


@pytest.mark.django_db
def test_first_row(capsys):
    Author.objects.create(name='author', id=1)

    call_command(COMMAND_NAME, '--cqrs-id=author')

    captured = capsys.readouterr()
    assert '{},'.format(Author.CQRS_ID) in captured.out


@pytest.mark.django_db
def test_objects_less_than_batch(capsys):
    author = Author.objects.create(name='author', id=1)

    call_command(COMMAND_NAME, '--cqrs-id=author')

    captured = capsys.readouterr()
    out_lines = captured.out.split('\n')

    assert ujson.loads(out_lines[1]) == [[author.pk, author.cqrs_revision]]


@pytest.mark.django_db
def test_objects_more_than_batch(capsys):
    for i in range(3):
        Author.objects.create(name=str(i), id=i)

    call_command(COMMAND_NAME, '--cqrs-id=author', '--batch=2')

    captured = capsys.readouterr()
    out_lines = captured.out.split('\n')
    assert ujson.loads(out_lines[1]) == [
        [author.pk, author.cqrs_revision] for author in Author.objects.all()[:2]
    ]
    assert ujson.loads(out_lines[2]) == [
        [author.pk, author.cqrs_revision] for author in Author.objects.all()[2:]
    ]


@pytest.mark.django_db
def test_filter_no_objects(capsys):
    call_command(COMMAND_NAME, '--cqrs-id=author', '-f={"id__in": [1, 2]}')

    captured = capsys.readouterr()
    assert 'No objects found for filter!' in captured.err


@pytest.mark.django_db
def test_objects_are_filtered(capsys):
    for i in range(2):
        Author.objects.create(name=str(i), id=i)

    call_command(COMMAND_NAME, '--cqrs-id=author', '-f={"id__in": [1, 3]}')

    captured = capsys.readouterr()
    out_lines = captured.out.split('\n')

    assert ujson.loads(out_lines[1]) == [[1, 0]]
