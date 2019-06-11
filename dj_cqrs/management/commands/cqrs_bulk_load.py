from __future__ import unicode_literals

import os

import ujson
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dj_cqrs.registries import ReplicaRegistry


class Command(BaseCommand):
    help = 'Bulk load of a CQRS model to a replica service.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input', '-i', help='Input file for loading.', type=str, required=True,
        )

    def handle(self, *args, **options):
        f_name = options['input']
        if not os.path.exists(f_name):
            raise CommandError("File {} doesn't exist!".format(f_name))

        with open(f_name, 'r') as f:
            try:
                cqrs_id = next(f).strip()
            except StopIteration:
                cqrs_id = None

            if not cqrs_id:
                raise CommandError('File {} is empty!'.format(f_name))

            model = ReplicaRegistry.get_model_by_cqrs_id(cqrs_id)
            if not model:
                raise CommandError('Wrong CQRS ID: {}!'.format(cqrs_id))

            with transaction.atomic():
                model._default_manager.all().delete()

                line_number = 1
                for line in f:
                    try:
                        master_data = ujson.loads(line.strip())
                    except ValueError:
                        raise CommandError(
                            "Dump file can't be parsed: line {}!".format(line_number),
                        )

                    instance = model.cqrs_save(master_data)
                    if not instance:
                        raise CommandError(
                            "Instance can't be saved: line {}!".format(line_number),
                        )

                    line_number += 1

            print('Done! {} instance(s) saved.'.format(model._default_manager.count()))
