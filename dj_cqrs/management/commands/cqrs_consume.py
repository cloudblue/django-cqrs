#  Copyright © 2022 Ingram Micro Inc. All rights reserved.
import logging
import signal
import threading
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from watchfiles import watch
from watchfiles.filters import PythonFilter
from watchfiles.run import start_process

from dj_cqrs.registries import ReplicaRegistry


logger = logging.getLogger('django_cqrs.cqrs_consume')


def consume(**kwargs):
    import django
    django.setup()

    from dj_cqrs.transport import current_transport
    current_transport.consume(**kwargs)


class WorkersManager:

    def __init__(
            self,
            consume_kwargs,
            workers=1,
            reload=False,
            ignore_paths=None,
            sigint_timeout=5,
            sigkill_timeout=1,
    ):
        self.pool = []
        self.workers = workers
        self.reload = reload
        self.consume_kwargs = consume_kwargs
        self.stop_event = threading.Event()
        self.sigint_timeout = sigint_timeout
        self.sigkill_timeout = sigkill_timeout

        if self.reload:
            self.watch_filter = PythonFilter(ignore_paths=ignore_paths)
            self.watcher = watch(
                Path.cwd(),
                watch_filter=self.watch_filter,
                stop_event=self.stop_event,
                yield_on_timeout=True,
            )

    def handle_signal(self, *args, **kwargs):
        self.stop_event.set()

    def run(self):
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self.handle_signal)
        if self.reload:
            signal.signal(signal.SIGHUP, self.restart)

        self.start()

        if self.reload:
            for files_changed in self:
                if files_changed:
                    self.restart()
        else:
            self.stop_event.wait()

        self.terminate()

    def start(self):
        for _ in range(self.workers):
            process = start_process(
                consume,
                'function',
                (),
                self.consume_kwargs,
            )
            self.pool.append(process)

    def terminate(self, *args, **kwargs):
        while self.pool:
            process = self.pool.pop()
            process.stop(sigint_timeout=self.sigint_timeout, sigkill_timeout=self.sigkill_timeout)

    def restart(self, *args, **kwargs):
        self.terminate()
        self.start()

    def __iter__(self):
        return self

    def __next__(self):
        changes = next(self.watcher)
        if changes:
            return list({Path(c[1]) for c in changes})
        return None


class Command(BaseCommand):
    help = 'Starts CQRS worker, which consumes messages from message queue.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workers',
            '-w',
            help='Number of workers',
            type=int,
            default=1,
        )
        parser.add_argument(
            '--cqrs-id',
            '-cid',
            nargs='*',
            type=str,
            help='Choose model(s) by CQRS_ID for consuming',
        )
        parser.add_argument(
            '--reload',
            '-r',
            help=(
                'Enable reload signal SIGHUP and autoreload '
                'on file changes'
            ),
            action='store_true',
            default=False,
        )
        parser.add_argument(
            '--ignore-paths',
            nargs='?',
            type=str,
            help=(
                'Specify directories to ignore, '
                'to ignore multiple paths use a comma as separator, '
                'e.g. "env" or "env,node_modules"'
            ),
        )
        parser.add_argument(
            '--sigint-timeout',
            nargs='?',
            type=int,
            default=5,
            help='How long to wait for the sigint timeout before sending sigkill.',
        )
        parser.add_argument(
            '--sigkill-timeout',
            nargs='?',
            type=int,
            default=1,
            help='How long to wait for the sigkill timeout before issuing a timeout exception.',
        )

    def handle(
            self,
            *args,
            workers=1,
            cqrs_id=None,
            reload=False,
            ignore_paths=None,
            sigint_timeout=5,
            sigkill_timeout=1,
            **options,
    ):

        paths_to_ignore = None
        if ignore_paths:
            paths_to_ignore = [Path(p).resolve() for p in ignore_paths.split(',')]

        workers_manager = WorkersManager(
            workers=workers,
            consume_kwargs=self.get_consume_kwargs(cqrs_id),
            reload=reload,
            ignore_paths=paths_to_ignore,
            sigint_timeout=sigint_timeout,
            sigkill_timeout=sigkill_timeout,
        )

        workers_manager.run()

    def get_consume_kwargs(self, ids_list):
        consume_kwargs = {}
        if ids_list:
            cqrs_ids = set()
            for cqrs_id in ids_list:
                model = ReplicaRegistry.get_model_by_cqrs_id(cqrs_id)
                if not model:
                    raise CommandError('Wrong CQRS ID: {0}!'.format(cqrs_id))

                cqrs_ids.add(cqrs_id)

            consume_kwargs['cqrs_ids'] = cqrs_ids

        return consume_kwargs
