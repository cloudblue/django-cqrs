#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import sys

from django.core.management.base import BaseCommand, CommandError

from dj_cqrs.constants import NO_QUEUE
from dj_cqrs.management.commands.cqrs_sync import Command as SyncCommand
from dj_cqrs.registries import MasterRegistry


class Command(BaseCommand):
    help = 'Diff synchronizer from CQRS replica stream.'

    def handle(self, *args, **options):
        with sys.stdin as f:
            first_line = f.readline().strip()
            model = self._get_model(first_line)
            queue = self._get_queue(first_line)

            for pks_line in f:
                sync_kwargs = {
                    'cqrs_id': model.CQRS_ID,
                    'filter': '{{"id__in": {}}}'.format(pks_line.strip()),
                }
                if queue:
                    sync_kwargs['queue'] = queue

                SyncCommand().handle(**sync_kwargs)

    @staticmethod
    def _get_model(first_line):
        cqrs_id = first_line.split(',')[0]
        model = MasterRegistry.get_model_by_cqrs_id(cqrs_id)

        if not model:
            raise CommandError('Wrong CQRS ID: {}!'.format(cqrs_id))

        return model

    @staticmethod
    def _get_queue(first_line):
        queue = first_line.split(',')[-1]
        if queue != NO_QUEUE:
            return queue
