#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from multiprocessing import Process

from dj_cqrs.transport import current_transport

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Starts CQRS worker, which consumes messages from message queue.'

    def add_arguments(self, parser):
        parser.add_argument('--workers', '-w', help='Number of workers', type=int, default=0)

    def handle(self, *args, **options):
        if options['workers'] == 0:
            current_transport.consume()
        else:
            pool = []

            for _ in range(options['workers']):
                p = Process(target=current_transport.consume)
                pool.append(p)
                p.start()

            for p in pool:
                p.join()
