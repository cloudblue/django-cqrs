from __future__ import unicode_literals

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Filter synchronization of certain CQRS model rows over transport to replicas.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        pass
