#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

from rest_framework.serializers import CharField, ModelSerializer

from tests.dj_master.models import Author, Book, Publisher


class BookSerializer(ModelSerializer):
    name = CharField(source='title')

    class Meta:
        model = Book
        fields = ('id', 'name')


class PublisherSerializer(ModelSerializer):
    class Meta:
        model = Publisher
        fields = '__all__'


class AuthorSerializer(ModelSerializer):
    books = BookSerializer(many=True)
    publisher = PublisherSerializer()

    class Meta:
        model = Author
        fields = ('id', 'name', 'publisher', 'books')
