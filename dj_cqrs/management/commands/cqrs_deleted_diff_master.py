#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import sys

import ujson
from django.core.management.base import BaseCommand, CommandError

from dj_cqrs.registries import MasterRegistry


class Command(BaseCommand):
    help = 'Diff of deleted CQRS models pks from master diff stream.'

    @classmethod
    def serialize_out(cls, package):
        return ujson.dumps(package)

    @classmethod
    def deserialize_in(cls, package_line):
        return set(ujson.loads(package_line))

    def handle(self, *args, **options):
        with sys.stdin as f:
            first_line = f.readline()
            model = self._get_model(first_line)
            self.stdout.write(first_line.strip())

            for package_line in f:
                master_data = self.deserialize_in(package_line)

                exist_pks = set(
                    model.objects.filter(
                        pk__in=master_data,
                    ).values_list(
                        'pk', flat=True,
                    ),
                )
                diff_ids = list(master_data - exist_pks)
                if diff_ids:
                    self.stdout.write(self.serialize_out(diff_ids))
                    self.stderr.write('PK to delete: {0}'.format(str(diff_ids)))

    @staticmethod
    def _get_model(first_line):
        cqrs_id = first_line.split(',')[0]
        model = MasterRegistry.get_model_by_cqrs_id(cqrs_id)

        if not model:
            raise CommandError('Wrong CQRS ID: {0}!'.format(cqrs_id))

        return model
