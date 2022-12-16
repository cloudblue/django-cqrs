#  Copyright © 2022 Ingram Micro Inc. All rights reserved.

import ujson
from django.core.exceptions import FieldError
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from dj_cqrs.management.utils import batch_qs
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

    def handle(self, *args, **options):
        model = self._get_model(options)
        batch_size = self._get_batch_size(options)

        qs = model._default_manager.all().order_by()
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
                raise CommandError('Bad filter kwargs! {0}'.format(str(e)))

        if not qs.exists():
            self.stderr.write('No objects found for filter!')
            return

        current_dt = now()
        self.stdout.write('{0},{1}'.format(model.CQRS_ID, str(current_dt)))

        for bqs in batch_qs(qs, batch_size=batch_size):
            package = [
                [instance.pk, instance.cqrs_revision]
                for instance in bqs
                if instance.is_sync_instance()
            ]
            self.stdout.write(self.serialize_package(package))

    @staticmethod
    def _get_model(options):
        cqrs_id = options['cqrs_id']
        model = MasterRegistry.get_model_by_cqrs_id(cqrs_id)

        if not model:
            raise CommandError('Wrong CQRS ID: {0}!'.format(cqrs_id))

        return model

    @staticmethod
    def _get_batch_size(options):
        return options['batch']
