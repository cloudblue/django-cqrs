#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import sys

import ujson
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from dj_cqrs.registries import ReplicaRegistry


class Command(BaseCommand):
    help = 'Diff for deleted objects synchronizer from CQRS master stream.'

    @classmethod
    def deserialize_in(cls, package_line):
        return ujson.loads(package_line)

    def handle(self, *args, **options):
        with sys.stdin as f:
            first_line = f.readline().strip()
            model = self._get_model(first_line)

            for pks_line in f:
                try:
                    model._default_manager.filter(
                        pk__in=self.deserialize_in(pks_line.strip()),
                    ).delete()
                except DatabaseError as e:
                    print(str(e), file=sys.stderr)

    @staticmethod
    def _get_model(first_line):
        cqrs_id = first_line.split(',')[0]
        model = ReplicaRegistry.get_model_by_cqrs_id(cqrs_id)

        if not model:
            raise CommandError('Wrong CQRS ID: {0}!'.format(cqrs_id))

        return model
