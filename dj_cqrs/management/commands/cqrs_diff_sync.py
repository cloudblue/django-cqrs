import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Starts CQRS worker, which consumes messages from message queue.'

    def handle(self, *args, **options):
        with sys.stdin as f:
            model_dt = f.read()
            self.stdout.write(model_dt)

            for line in f:
                import pdb; from pprint import pprint; pdb.set_trace()  # noqa
