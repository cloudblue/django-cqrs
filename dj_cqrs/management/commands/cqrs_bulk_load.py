#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import os
import sys

import ujson
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

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
        parser.add_argument(
            '--batch', '-b',
            help='Batch size',
            type=int,
            default=10000,
        )

    def handle(self, *args, **options):
        batch_size = self._get_batch_size(options)

        f_name = options['input']
        if f_name != '-' and not os.path.exists(f_name):
            raise CommandError("File {0} doesn't exist!".format(f_name))

        with sys.stdin if f_name == '-' else open(f_name, 'r') as f:
            try:
                cqrs_id = next(f).strip()
            except StopIteration:
                cqrs_id = None

            if not cqrs_id:
                raise CommandError('File {0} is empty!'.format(f_name))

            model = ReplicaRegistry.get_model_by_cqrs_id(cqrs_id)
            if not model:
                raise CommandError('Wrong CQRS ID: {0}!'.format(cqrs_id))

            with transaction.atomic():
                if options['clear']:
                    try:
                        model._default_manager.all().delete()
                    except DatabaseError:
                        raise CommandError("Delete operation fails!")

            self._process(f, model, batch_size)

    @classmethod
    def _process(cls, stream, model, batch_size):
        success_counter = 0
        line_number = 2

        while True:
            with transaction.atomic():
                try:
                    for _ in range(0, batch_size):
                        line = stream.readline()

                        success = cls._process_line(line_number, line, model)

                        success_counter += int(bool(success))
                        line_number += 1
                except EOFError:
                    break

        print('Done!\n{0} instance(s) loaded.'.format(success_counter), file=sys.stderr)

    @staticmethod
    def _process_line(line_number, line, model):
        if not line:
            raise EOFError
        try:
            try:
                master_data = ujson.loads(line.strip())
            except ValueError:
                print(
                    "Dump file can't be parsed: line {0}!".format(line_number),
                    file=sys.stderr,
                )
                return False

            instance = model.cqrs_save(master_data)
            if not instance:
                print(
                    "Instance can't be saved: line {0}!".format(line_number),
                    file=sys.stderr,
                )
            else:
                return True
        except Exception as e:
            print(
                'Unexpected error: line {0}! {1}'.format(line_number, str(e)),
                file=sys.stderr,
            )

        return False

    @staticmethod
    def _get_batch_size(options):
        return options['batch']
