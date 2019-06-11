from __future__ import unicode_literals

from django.core.exceptions import FieldError
from django.core.management.base import BaseCommand, CommandError

import ujson
from dj_cqrs.registries import MasterRegistry


class Command(BaseCommand):
    help = 'Filter synchronization of certain CQRS model rows over transport to replicas.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cqrs_id', '-cid', help='CQRS_ID of the master model.', type=str, required=True,
        )
        parser.add_argument(
            '--filter', '-f', help='Filter kwargs.', type=str, default=None,
        )
        parser.add_argument(
            '--queue', '-q', help='Name of a specific replica queue.', type=str, default=None,
        )

    def handle(self, *args, **options):
        model = self._get_model(options)

        qs = model._default_manager.none()
        if options['filter']:
            try:
                kwargs = ujson.loads(options['filter'])
                if not isinstance(kwargs, dict):
                    raise ValueError
            except ValueError:
                raise CommandError('Bad filter kwargs!')

            try:
                qs = model._default_manager.filter(**kwargs)
            except FieldError as e:
                raise CommandError('Bad filter kwargs! {}'.format(str(e)))

        if qs.count() == 0:
            print('No objects found for filter!')
            return

        counter = 0
        for instance in model.relate_cqrs_serialization(qs):
            instance.cqrs_sync(queue=options['queue'])
            counter += 1

        print('Done! {} instance(s) synced.'.format(counter))

    def _get_model(self, options):
        cqrs_id = options['cqrs_id']
        model = MasterRegistry.get_model_by_cqrs_id(cqrs_id)

        if not model:
            raise CommandError('Wrong CQRS ID: {}!'.format(cqrs_id))

        return model
