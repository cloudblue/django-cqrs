from __future__ import unicode_literals
from __future__ import print_function

import os
import sys

import ujson
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, DatabaseError

from dj_cqrs.registries import ReplicaRegistry


class Command(BaseCommand):
    help = 'Bulk load of a CQRS model to a replica service.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input', '-i',
            help='Input file for loading (- for reading from stdin)',
            type=str, required=True,
        )
        parser.add_argument(
            '--clear', '-c',
            help='Delete existing models',
            type=bool,
            required=False,
            default=False,
        )

    def handle(self, *args, **options):
        f_name = options['input']
        if f_name != '-' and not os.path.exists(f_name):
            raise CommandError("File {} doesn't exist!".format(f_name))

        with sys.stdin if f_name == '-' else open(f_name, 'r') as f:
            try:
                cqrs_id = next(f).strip()
            except StopIteration:
                cqrs_id = None

            if not cqrs_id:
                raise CommandError('File {} is empty!'.format(f_name))

            model = ReplicaRegistry.get_model_by_cqrs_id(cqrs_id)
            if not model:
                raise CommandError('Wrong CQRS ID: {}!'.format(cqrs_id))

            success_counter = 0
            with transaction.atomic():
                if options['clear']:
                    try:
                        model._default_manager.all().delete()
                    except DatabaseError:
                        raise CommandError("Delete operation fails!")

                line_number = 2
                for line in f:
                    try:
                        try:
                            master_data = ujson.loads(line.strip())
                        except ValueError:
                            print(
                                "Dump file can't be parsed: line {}!".format(line_number),
                                file=sys.stderr
                            )
                            line_number += 1
                            continue

                        instance = model.cqrs_save(master_data)
                        if not instance:
                            print(
                                "Instance can't be saved: line {}!".format(line_number),
                                file=sys.stderr
                            )
                        else:
                            success_counter += 1
                    except Exception as e:
                        print(
                            'Unexpected error: line {}! {}'.format(line_number, str(e)),
                            file=sys.stderr
                        )
                    finally:
                        line_number += 1

            print('Done!\n{} instance(s) loaded.'.format(success_counter), file=sys.stderr)
