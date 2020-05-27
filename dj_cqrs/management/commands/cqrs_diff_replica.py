#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import sys

import ujson
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from dj_cqrs.registries import ReplicaRegistry


class Command(BaseCommand):
    help = 'Diff of CQRS replica models from master diff stream.'

    @classmethod
    def deserialize_in(cls, package_line):
        return dict(ujson.loads(package_line))

    @classmethod
    def serialize_out(cls, ids):
        return ujson.dumps(ids)

    def handle(self, *args, **options):
        with sys.stdin as f:
            first_line = f.readline()
            model = self._get_model(first_line)
            self.stdout.write('{},{}'.format(first_line.strip(), settings.CQRS.get('queue')))

            for package_line in f:
                master_data = self.deserialize_in(package_line)

                qs = model._default_manager.filter(pk__in=master_data.keys()) \
                    .order_by().only('pk', 'cqrs_revision')
                replica_data = {instance.pk: instance.cqrs_revision for instance in qs}

                diff_ids = set()
                for pk, cqrs_revision in master_data.items():
                    if replica_data.get(pk, -1) != cqrs_revision:
                        diff_ids.add(pk)

                if diff_ids:
                    self.stdout.write(self.serialize_out(list(diff_ids)))
                    self.stderr.write('PK to resync: {}'.format(str(diff_ids)))

    @staticmethod
    def _get_model(first_line):
        cqrs_id = first_line.split(',')[0]
        model = ReplicaRegistry.get_model_by_cqrs_id(cqrs_id)

        if not model:
            raise CommandError('Wrong CQRS ID: {}!'.format(cqrs_id))

        return model
