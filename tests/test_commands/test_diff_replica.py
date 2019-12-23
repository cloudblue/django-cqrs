import sys
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from tests.dj_master.models import Author
from tests.dj_replica.models import AuthorRef


COMMAND_NAME = 'cqrs_diff_replica'


def test_bad_cqrs_id(mocker):
    mocker.patch.object(sys, 'stdin', StringIO('invalid,datetime\n'))

    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME)

    assert 'Wrong CQRS ID: invalid!' in str(e)


@pytest.mark.django_db
def test_no_rows(mocker):
    mocker.patch.object(sys, 'stdin', StringIO('author,datetime\n'))

    call_command(COMMAND_NAME)
    assert AuthorRef.objects.count() == 0


@pytest.mark.django_db
def test_all_synced(mocker):
    mocker.patch('dj_cqrs.controller.producer.produce')

    for i in range(2):
        Author.objects.create()


@pytest.mark.django_db
def test_sync_for_all(mocker, capsys):
    # for i in range(3):
    #     Author.objects.create(name=str(i))=
    #
    # call_command('cqrs_diff_master', '--cqrs-id=author')
    # captured = capsys.readouterr()
    # mocker.patch.object(sys, 'stdin', [
    #     StringIO(line) for line in captured.out.split('\n')
    # ])
    #
    # call_command(COMMAND_NAME)
    # assert AuthorRef.objects.count() == 2
    pass


def test_sync_for_filtered():
    pass


def test_sync_batch():
    pass
