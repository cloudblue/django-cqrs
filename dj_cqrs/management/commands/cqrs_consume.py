#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from multiprocessing import Process

from dj_cqrs.registries import ReplicaRegistry
from dj_cqrs.transport import current_transport

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Starts CQRS worker, which consumes messages from message queue.'

    def add_arguments(self, parser):
        parser.add_argument('--workers', '-w', help='Number of workers', type=int, default=0)
        parser.add_argument(
            '--cqrs-id',
            '-cid',
            nargs='*',
            type=str,
            help='Choose model(s) by CQRS_ID for consuming',
        )

    def handle(self, *args, **options):
        consume_kwargs = {}

        if options.get('cqrs_id'):
            cqrs_ids = set()

            for cqrs_id in options['cqrs_id']:
                model = ReplicaRegistry.get_model_by_cqrs_id(cqrs_id)
                if not model:
                    raise CommandError('Wrong CQRS ID: {0}!'.format(cqrs_id))

                cqrs_ids.add(cqrs_id)

            consume_kwargs['cqrs_ids'] = cqrs_ids

        if options['workers'] <= 1:
            current_transport.consume(**consume_kwargs)
            return

        pool = []

        for _ in range(options['workers']):
            p = Process(target=current_transport.consume, kwargs=consume_kwargs)
            pool.append(p)
            p.start()

        for p in pool:
            p.join()
