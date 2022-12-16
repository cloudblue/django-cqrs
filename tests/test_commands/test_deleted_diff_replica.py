#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import pytest
import ujson
from django.core.management import CommandError, call_command
from django.utils.timezone import now

from tests.dj_replica.models import AuthorRef


COMMAND_NAME = 'cqrs_deleted_diff_replica'


def test_no_cqrs_id():
    with pytest.raises(CommandError):
        call_command(COMMAND_NAME)


def test_bad_cqrs_id():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs-id=invalid')

    assert 'Wrong CQRS ID: invalid!' in str(e)


@pytest.mark.django_db
def test_first_row(capsys):
    AuthorRef.objects.create(name='author', id=1, cqrs_revision=0, cqrs_updated=now())

    call_command(COMMAND_NAME, '--cqrs-id=author')

    captured = capsys.readouterr()
    assert '{0},'.format(AuthorRef.CQRS_ID) in captured.out


@pytest.mark.django_db
def test_objects_less_than_batch(capsys):
    AuthorRef.objects.create(name='author', id=1, cqrs_revision=0, cqrs_updated=now())

    call_command(COMMAND_NAME, '--cqrs-id=author')

    captured = capsys.readouterr()
    out_lines = captured.out.split('\n')

    assert ujson.loads(out_lines[1]) == [1]


@pytest.mark.django_db
def test_objects_more_than_batch(capsys):
    for i in range(3):
        AuthorRef.objects.create(name=str(i), id=i, cqrs_revision=i, cqrs_updated=now())

    call_command(COMMAND_NAME, '--cqrs-id=author', '--batch=2')

    captured = capsys.readouterr()
    out_lines = captured.out.split('\n')
    assert ujson.loads(out_lines[1]) == [0, 1]
    assert ujson.loads(out_lines[2]) == [2]


@pytest.mark.django_db
def test_filter_no_objects(capsys):
    call_command(COMMAND_NAME, '--cqrs-id=author', '-f={"id__in": [1, 2]}')

    captured = capsys.readouterr()
    assert 'No objects found for filter!' in captured.err


@pytest.mark.django_db
def test_objects_are_filtered(capsys):
    for i in range(2):
        AuthorRef.objects.create(name=str(i), id=i, cqrs_revision=i, cqrs_updated=now())

    call_command(COMMAND_NAME, '--cqrs-id=author', '-f={"id__in": [1, 3]}')

    captured = capsys.readouterr()
    out_lines = captured.out.split('\n')

    assert ujson.loads(out_lines[1]) == [1]
