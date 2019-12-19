import pytest
from django.core.management import CommandError, call_command
from django.db import transaction
from tests.utils import db_error

from tests.dj_master.models import Author, Publisher

COMMAND_NAME = 'cqrs_diff_master'


def test_no_cqrs_id():
    with pytest.raises(CommandError):
        call_command(COMMAND_NAME)


def test_bad_cqrs_id():
    with pytest.raises(CommandError) as e:
        call_command(COMMAND_NAME, '--cqrs-id=invalid')

    assert 'Wrong CQRS ID: invalid!' in str(e)


@pytest.mark.django_db
def tests_ok(capsys):
    Author.objects.create(id=2, name='2')

    call_command(COMMAND_NAME, '--cqrs-id=author')

    captured = capsys.readouterr()
    assert 'Done!\n2 instance(s) saved.\n2 instance(s) processed.' in captured.err