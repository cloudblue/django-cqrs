from __future__ import unicode_literals

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Bulk load of a CQRS model to a replica service.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        pass
