#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import random

from django.core.management.base import BaseCommand
from django.db import transaction

from tests.dj_master.models import Author, Book, Publisher


class Command(BaseCommand):
    help = 'Simulate N signals.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', '-c', help='Simulation of N signals.', type=int, default=3000,
        )

    @staticmethod
    def _get_max_id(model):
        try:
            return model.objects.all().order_by('-id')[0].id
        except IndexError:
            return 0

    def handle(self, *args, **options):
        max_author_id = self._get_max_id(Author)
        max_book_id = self._get_max_id(Book)
        max_publisher_id = self._get_max_id(Publisher)

        with transaction.atomic():
            for _ in range(options['count']):
                publisher = None
                if bool(random.getrandbits(1)):
                    max_publisher_id += 1
                    publisher = Publisher.objects.create(id=max_publisher_id, name='p')

                max_author_id += 1
                author = Author.objects.create(id=max_author_id, name='a', publisher=publisher)

                for _ in range(random.randint(0, 2)):
                    max_book_id += 1
                    Book.objects.create(id=max_book_id, title='t', author=author)
