#  Copyright © 2022 Ingram Micro Inc. All rights reserved.

import datetime
import os
import sys
import time

import ujson
from django.core.management.base import BaseCommand, CommandError

from dj_cqrs.management.utils import batch_qs
from dj_cqrs.registries import MasterRegistry


class Command(BaseCommand):
    help = 'Bulk dump of a CQRS model from master service.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cqrs-id', '-c',
            help='CQRS_ID of the master model',
            type=str,
            required=True,
        )
        parser.add_argument(
            '--output', '-o',
            help='Output file for dumping (- for writing to stdout)',
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
        parser.add_argument(
            '--force', '-f',
            help='Override output file',
            action='store_true',
        )

    def handle(self, *args, **options):
        model = self._get_model(options)
        out_fname = self._get_output_filename(options)
        progress = self._get_progress(options)
        batch_size = self._get_batch_size(options)

        with sys.stdout if out_fname == '-' else open(out_fname, 'w') as f:
            f.write(model.CQRS_ID)

            counter, success_counter = 0, 0
            db_count = model._default_manager.count()

            if progress:
                print(
                    'Processing {0} records with batch size {1}'.format(db_count, batch_size),
                    file=sys.stderr,
                )
            for qs in batch_qs(
                    model.relate_cqrs_serialization(model._default_manager.order_by().all()),
                    batch_size=batch_size,
            ):
                ts = time.time()
                cs = counter
                for instance in qs:
                    counter += 1
                    try:
                        f.write(
                            '\n' + ujson.dumps(instance.to_cqrs_dict()),
                        )
                        success_counter += 1
                    except Exception as e:
                        print('\nDump record failed for pk={0}: {1}: {2}'.format(
                            instance.pk, type(e).__name__, str(e),
                        ), file=sys.stderr)
                if progress:
                    rate = (counter - cs) / (time.time() - ts)
                    percent = 100 * counter / db_count
                    eta = datetime.timedelta(seconds=int((db_count - counter) / rate))
                    sys.stderr.write(
                        '\r{0} of {1} processed - {2}% with '
                        'rate {3:.1f} rps, to go {4} ...{5:20}'.format(
                            counter, db_count, int(percent), rate, str(eta), ' ',
                        ))
                    sys.stderr.flush()

        print('Done!\n{0} instance(s) saved.\n{1} instance(s) processed.'.format(
            success_counter, counter,
        ), file=sys.stderr)

    @staticmethod
    def _get_model(options):
        cqrs_id = options['cqrs_id']
        model = MasterRegistry.get_model_by_cqrs_id(cqrs_id)

        if not model:
            raise CommandError('Wrong CQRS ID: {0}!'.format(cqrs_id))

        return model

    @staticmethod
    def _get_output_filename(options):
        f_name = options['output']
        if f_name is None:
            f_name = '{0}.dump'.format(options['cqrs_id'])

        if f_name != '-' and os.path.exists(f_name) and not (options['force']):
            raise CommandError('File {0} exists!'.format(f_name))

        return f_name

    @staticmethod
    def _get_progress(options):
        return bool(options['progress'])

    @staticmethod
    def _get_batch_size(options):
        return options['batch']
