import sys

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from dj_cqrs.registries import MasterRegistry


class Command(BaseCommand):
    help = 'Diff synchronizer from CQRS replica stream.'

    def handle(self, *args, **options):
        with sys.stdin as f:
            first_line = f.read()
            model = self._get_model(first_line)
            queue = self._get_queue(first_line)

            for pks_line in f:
                sync_args = [
                    'cqrs_sync',
                    '--cqrs-id={}'.format(model.CQRS_ID),
                    '-f={{"id__in": {}}}'.format(pks_line),
                ]
                if queue:
                    sync_args.append('--queue={}'.format(queue))

                call_command(*sync_args)

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
        if queue != 'None':
            return queue
