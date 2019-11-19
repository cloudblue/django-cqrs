from __future__ import unicode_literals

import os

import ujson
from django.core.management.base import BaseCommand, CommandError

from dj_cqrs.management.commands.utils import batch_qs
from dj_cqrs.registries import MasterRegistry


class Command(BaseCommand):
    help = 'Bulk dump of a CQRS model from master service.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cqrs_id', '-cid', help='CQRS_ID of the master model.', type=str, required=True,
        )
        parser.add_argument(
            '--output', '-o', help='Output file for dumping.', type=str, default=None,
        )

    def handle(self, *args, **options):
        model = self._get_model(options)
        out_fname = self._get_output_filename(options)

        with open(out_fname, 'w') as f:
            f.write(model.CQRS_ID)

            counter = 0
            db_count = model._default_manager.count()

            for qs in batch_qs(model.relate_cqrs_serialization(
                    model._default_manager.order_by().all(),
            )):
                for instance in qs:
                    f.write(
                        '\n' + ujson.dumps(instance.to_cqrs_dict()),
                    )
                    counter += 1
                print('{} from {} processed...'.format(counter, db_count))

        print('Done! {} instance(s) saved.'.format(counter))

    def _get_model(self, options):
        cqrs_id = options['cqrs_id']
        model = MasterRegistry.get_model_by_cqrs_id(cqrs_id)

        if not model:
            raise CommandError('Wrong CQRS ID: {}!'.format(cqrs_id))

        return model

    def _get_output_filename(self, options):
        f_name = options['output']
        if f_name is None:
            f_name = '{}.dump'.format(options['cqrs_id'])

        if os.path.exists(f_name):
            raise CommandError('File {} exists!'.format(f_name))

        return f_name
