#  Copyright © 2022 Ingram Micro Inc. All rights reserved.
import multiprocessing
import signal

from django.core.management.base import BaseCommand, CommandError

from dj_cqrs.registries import ReplicaRegistry
from dj_cqrs.transport import current_transport


class WorkersManager:

    def __init__(self, options, transport, consume_kwargs):
        self.pool = []
        self.options = options
        self.transport = transport
        self.consume_kwargs = consume_kwargs

    def start(self):
        for i in range(self.options['workers'] or 1):
            process = multiprocessing.Process(
                name=f'cqrs-consumer-{i}',
                target=self.transport.consume,
                kwargs=self.consume_kwargs,
            )
            self.pool.append(process)
            process.start()

        for process in self.pool:
            process.join()

    def terminate(self, *args, **kwargs):
        while self.pool:
            p = self.pool.pop()
            p.terminate()
            p.join()

    def reload(self, *args, **kwargs):
        self.terminate()
        self.start()


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
        parser.add_argument(
            '--reload', '-r', help='Enable reload signal SIGHUP', action='store_true',
        )

    def handle(self, *args, **options):
        if not options['workers'] and not options['reload']:
            current_transport.consume(**self.get_consume_kwargs(options))
            return

        self.start_workers_pool(options)

    def start_workers_pool(self, options):
        workers_manager = WorkersManager(
            options, current_transport, self.get_consume_kwargs(options),
        )
        if options['reload']:
            try:
                multiprocessing.set_start_method('spawn')
            except RuntimeError:
                pass

            signal.signal(signal.SIGHUP, workers_manager.reload)

        workers_manager.start()

    def get_consume_kwargs(self, options):
        consume_kwargs = {}
        if options.get('cqrs_id'):
            cqrs_ids = set()
            for cqrs_id in options['cqrs_id']:
                model = ReplicaRegistry.get_model_by_cqrs_id(cqrs_id)
                if not model:
                    raise CommandError('Wrong CQRS ID: {0}!'.format(cqrs_id))

                cqrs_ids.add(cqrs_id)

            consume_kwargs['cqrs_ids'] = cqrs_ids

        return consume_kwargs
