#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest
from django.core.management import call_command
from django.db import transaction

from tests.dj_master import models as master_models
from tests.dj_replica import models as replica_models
from tests.test_commands.utils import remove_file


@pytest.mark.django_db
def tests_dumps_several_rows(mocker):
    mocker.patch('dj_cqrs.controller.producer.produce')
    remove_file('bulk_flow.dump')

    master_models.Author.objects.create(id=2, name='2')

    with transaction.atomic():
        publisher = master_models.Publisher.objects.create(id=1, name='publisher')
        master_models.Author.objects.create(id=1, name='1', publisher=publisher)

    assert replica_models.AuthorRef.objects.count() == 0
    assert replica_models.Publisher.objects.count() == 0

    call_command('cqrs_bulk_dump', '--cqrs-id=author', '-o=bulk_flow.dump')
    call_command('cqrs_bulk_load', '-i=bulk_flow.dump')

    assert replica_models.AuthorRef.objects.count() == 2
    assert replica_models.Publisher.objects.count() == 1
