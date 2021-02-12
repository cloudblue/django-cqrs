#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import sys

import ujson

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from dj_cqrs.registries import MasterRegistry


GET_NON_EXISTING_PKS_SQL_TEMPLATE = """
SELECT t.pk
FROM (
     WITH t0(pk) AS (
         VALUES {values}
     )
     SELECT *
     FROM t0
 ) t
LEFT JOIN {table} m ON m.{pk_field} = t.pk
WHERE m.{pk_field} IS NULL
"""


class Command(BaseCommand):
    help = 'Diff of deleted CQRS models pks from master diff stream.'

    @classmethod
    def serialize_out(cls, package):
        return ujson.dumps(package)

    @classmethod
    def deserialize_in(cls, package_line):
        return ujson.loads(package_line)

    def handle(self, *args, **options):
        with sys.stdin as f:
            first_line = f.readline()
            model = self._get_model(first_line)
            self.stdout.write(first_line.strip())

            with connection.cursor() as cursor:
                for package_line in f:
                    master_data = self.deserialize_in(package_line)

                    sql = GET_NON_EXISTING_PKS_SQL_TEMPLATE.format(
                        values=','.join(["({})".format(pk) for pk in master_data]),
                        table=model._meta.db_table,
                        pk_field=model._meta.pk.attname,
                    )

                    cursor.execute(sql)
                    diff_ids = [r[0] for r in cursor.fetchall()]
                    if diff_ids:
                        self.stdout.write(self.serialize_out(diff_ids))
                        self.stderr.write('PK to delete: {}'.format(str(diff_ids)))

    @staticmethod
    def _get_model(first_line):
        cqrs_id = first_line.split(',')[0]
        model = MasterRegistry.get_model_by_cqrs_id(cqrs_id)

        if not model:
            raise CommandError('Wrong CQRS ID: {}!'.format(cqrs_id))

        return model
