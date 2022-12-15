#  Copyright © 2022 Ingram Micro Inc. All rights reserved.

import datetime
import sys
import time

import ujson
from django.core.exceptions import FieldError
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from dj_cqrs.management.utils import batch_qs
from dj_cqrs.registries import MasterRegistry


DEFAULT_BATCH = 10000
DEFAULT_PROGRESS = False


class Command(BaseCommand):
    help = 'Filter synchronization of certain CQRS model rows over transport to replicas.'

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
            '--queue', '-q',
            help='Name of the specific replica queue',
            type=str,
            default=None,
        )
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
        model = self._get_model(options)
        progress = self._get_progress(options)
        batch_size = self._get_batch_size(options)

        qs = self._prepare_qs(model, options)
        db_count = qs.count()
        if db_count == 0:
            print('No objects found for filter!')
            return

        counter, success_counter = 0, 0
        if progress:
            print('Processing {0} records with batch size {1}'.format(db_count, batch_size))

        for qs_ in batch_qs(model.relate_cqrs_serialization(qs), batch_size=batch_size):
            ts = time.time()
            cs = counter

            for instance in qs_:
                counter += 1
                try:
                    instance.cqrs_sync(queue=options['queue'])
                    success_counter += 1
                except Exception as e:
                    print('\nSync record failed for pk={0}: {1}: {2}'.format(
                        instance.pk, type(e).__name__, str(e),
                    ))
                    close_old_connections()

            if progress:
                rate = (counter - cs) / (time.time() - ts)
                percent = 100 * counter / db_count
                eta = datetime.timedelta(seconds=int((db_count - counter) / rate))
                sys.stdout.write(
                    '\r{0} of {1} processed - {2}% with '
                    'rate {3:.1f} rps, to go {4} ...{5:20}'.format(
                        counter, db_count, int(percent), rate, str(eta), ' ',
                    ))
                sys.stdout.flush()

        print('Done!\n{0} instance(s) synced.\n{1} instance(s) processed.'.format(
            success_counter, counter,
        ))

    @staticmethod
    def _prepare_qs(model, options):
        qs = model._default_manager.none()
        if options['filter']:
            try:
                kwargs = ujson.loads(options['filter'])
                if not isinstance(kwargs, dict):
                    raise ValueError
            except ValueError:
                raise CommandError('Bad filter kwargs!')

            try:
                qs = model._default_manager.filter(**kwargs).order_by()
            except FieldError as e:
                raise CommandError('Bad filter kwargs! {0}'.format(str(e)))

        return qs

    @staticmethod
    def _get_model(options):
        cqrs_id = options['cqrs_id']
        model = MasterRegistry.get_model_by_cqrs_id(cqrs_id)

        if not model:
            raise CommandError('Wrong CQRS ID: {0}!'.format(cqrs_id))

        return model

    @staticmethod
    def _get_batch_size(options):
        return options.get('batch', DEFAULT_BATCH)

    @staticmethod
    def _get_progress(options):
        return bool(options.get('progress', DEFAULT_PROGRESS))
