import time
from datetime import timedelta

import ujson
from django.core.exceptions import FieldError
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from dj_cqrs.management.commands.utils import batch_qs
from dj_cqrs.registries import MasterRegistry


class Command(BaseCommand):
    help = 'Streaming diff of CQRS models from master service.'

    @classmethod
    def serialize_package(cls, package):
        return ujson.dumps(package)

    def add_arguments(self, parser):
        parser.add_argument(
            '--cqrs-id', '-cid',
            help='CQRS_ID of the master model',
            type=str,
            required=True,
        )
        parser.add_argument(
            '--filter', '-f',
            help='Filter kwargs',
            type=str,
            default=None,
        )
        parser.add_argument(
            '--batch', '-b',
            help='Batch size',
            type=int,
            default=10000,
        )
        parser.add_argument(
            '--progress', '-p',
            help='Display progress',
            action='store_true',
        )

    def handle(self, *args, **options):
        model = self._get_model(options)
        progress = self._get_progress(options)
        batch_size = self._get_batch_size(options)

        qs = model._default_manager.all().order_by().only('pk', 'cqrs_revision')
        if options['filter']:
            try:
                kwargs = ujson.loads(options['filter'])
                if not isinstance(kwargs, dict):
                    raise ValueError
            except ValueError:
                raise CommandError('Bad filter kwargs!')

            try:
                qs = qs.filter(**kwargs)
            except FieldError as e:
                raise CommandError('Bad filter kwargs! {}'.format(str(e)))

        counter = 0
        db_count = qs.count()
        if db_count == 0:
            self.stderr.write('No objects found for filter!')
            return

        if progress:
            self.stderr.write(
                'Processing {} records with batch size {}'.format(db_count, batch_size),
            )

        current_dt = now()
        self.stdout.write('{},{}'.format(model.CQRS_ID, str(current_dt)))

        for bqs in batch_qs(qs, batch_size=batch_size):
            ts = time.time()
            cs = counter

            package = {instance.pk: instance.cqrs_revision for instance in bqs}
            counter += len(package.keys())

            self.stdout.write(self.serialize_package(package))

            if progress:
                rate = (counter - cs) / (time.time() - ts)
                percent = 100 * counter / db_count
                eta = timedelta(seconds=int((db_count - counter) / rate))
                self.stderr.write(
                    '\r{} of {} processed - {}% with rate {:.1f} rps, to go {} ...{:20}'.format(
                        counter, db_count, int(percent), rate, str(eta), ' ',
                    ))
                self.stderr.flush()

    @staticmethod
    def _get_model(options):
        cqrs_id = options['cqrs_id']
        model = MasterRegistry.get_model_by_cqrs_id(cqrs_id)

        if not model:
            raise CommandError('Wrong CQRS ID: {}!'.format(cqrs_id))

        return model

    @staticmethod
    def _get_progress(options):
        return bool(options['progress'])

    @staticmethod
    def _get_batch_size(options):
        return options['batch']
