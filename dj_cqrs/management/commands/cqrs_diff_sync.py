#  Copyright © 2022 Ingram Micro Inc. All rights reserved.

import sys

from django.core.management.base import BaseCommand, CommandError

from dj_cqrs.constants import NO_QUEUE
from dj_cqrs.management.commands.cqrs_sync import (
    DEFAULT_BATCH,
    DEFAULT_PROGRESS,
    Command as SyncCommand,
)
from dj_cqrs.registries import MasterRegistry


class Command(BaseCommand):
    help = 'Diff synchronizer from CQRS replica stream.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch', '-b',
            help='Batch size',
            type=int,
            default=DEFAULT_BATCH,
        )
        parser.add_argument(
            '--progress', '-p',
            help='Display progress',
            action='store_true',
        )

    def handle(self, *args, **options):
        progress = self._get_progress(options)
        batch_size = self._get_batch_size(options)

        with sys.stdin as f:
            first_line = f.readline().strip()
            model = self._get_model(first_line)
            queue = self._get_queue(first_line)

            for pks_line in f:
                sync_kwargs = {
                    'cqrs_id': model.CQRS_ID,
                    'filter': '{{"id__in": {0}}}'.format(pks_line.strip()),
                    'progress': progress,
                    'batch': batch_size,
                }
                if queue:
                    sync_kwargs['queue'] = queue

                SyncCommand().handle(**sync_kwargs)

    @staticmethod
    def _get_model(first_line):
        cqrs_id = first_line.split(',')[0]
        model = MasterRegistry.get_model_by_cqrs_id(cqrs_id)

        if not model:
            raise CommandError('Wrong CQRS ID: {0}!'.format(cqrs_id))

        return model

    @staticmethod
    def _get_queue(first_line):
        queue = first_line.split(',')[-1]
        if queue != NO_QUEUE:
            return queue

    @staticmethod
    def _get_batch_size(options):
        return options.get('batch', DEFAULT_BATCH)

    @staticmethod
    def _get_progress(options):
        return bool(options.get('progress', DEFAULT_PROGRESS))
