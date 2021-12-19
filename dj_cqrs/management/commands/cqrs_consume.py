#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from multiprocessing import Process

from dj_cqrs.transport import current_transport

from django.core.management.base import BaseCommand


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
            consume_kwargs['cqrs_ids'] = set(options['cqrs_id'])

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
