#  Copyright © 2023 Ingram Micro Inc. All rights reserved.
from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.db import models

from dj_cqrs.mixins import ReplicaMixin


class User(ReplicaMixin, AbstractUser):
    """
    Simple replica which sync all fields
    """

    CQRS_ID = 'user'


class ProductType(models.Model):
    name = models.CharField(max_length=50)


class Product(ReplicaMixin, models.Model):
    """
    Replica with custom serialization and relation control
    """

    CQRS_ID = 'product'
    CQRS_CUSTOM_SERIALIZATION = True

    name = models.CharField(max_length=100)
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)

    @staticmethod
    def _handle_product_type(mapped_data):
        product_type, _ = ProductType.objects.update_or_create(
            id=mapped_data['id'],
            defaults=mapped_data,
        )
        return product_type

    @classmethod
    def cqrs_create(cls, sync, mapped_data, previous_data=None, meta=None):
        product_type = cls._handle_product_type(mapped_data['product_type'])
        return Product.objects.create(
            id=mapped_data['id'],
            product_type_id=product_type.id,
            name=mapped_data['name'],
            cqrs_revision=mapped_data['cqrs_revision'],
            cqrs_updated=mapped_data['cqrs_updated'],
        )

    def cqrs_update(self, sync, mapped_data, previous_data=None, meta=None):
        product_type = self._handle_product_type(mapped_data['product_type'])
        self.name = mapped_data['name']
        self.product_type_id = product_type.id
        self.save()
        return self


class Purchase(ReplicaMixin):
    """
    Replica model with custom storage mechanism.

    To simplify we use redis cache storage for this demo, but any SQL and NoSQL storage can
    be used.
    """

    CQRS_ID = 'purchase'
    CQRS_CUSTOM_SERIALIZATION = True

    class Meta:
        abstract = True

    @classmethod
    def cqrs_save(cls, master_data, previous_data=None, sync=False, meta=None):
        cache.set('purchase_' + str(master_data['id']), master_data)
        return True

    @classmethod
    def cqrs_delete(cls, master_data, meta=None):
        cache.delete('purchase_' + str(master_data['id']))
        return True
