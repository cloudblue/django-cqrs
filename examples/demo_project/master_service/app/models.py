#  Copyright © 2023 Ingram Micro Inc. All rights reserved.
from django.contrib.auth.models import AbstractUser
from django.db import models

from dj_cqrs.mixins import MasterMixin


class User(MasterMixin, AbstractUser):
    CQRS_ID = 'user'
    CQRS_PRODUCE = True


class ProductType(models.Model):
    name = models.CharField(max_length=50)


class Product(MasterMixin, models.Model):
    CQRS_ID = 'product'
    CQRS_SERIALIZER = 'app.serializers.ProductSerializer'

    name = models.CharField(max_length=50)
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)

    @classmethod
    def relate_cqrs_serialization(cls, queryset):
        return queryset.select_related('product_type')


class Purchase(MasterMixin, models.Model):
    CQRS_ID = 'purchase'
    CQRS_SERIALIZER = 'app.serializers.PurchaseSerializer'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    action_time = models.DateTimeField(auto_now_add=True)

    @classmethod
    def relate_cqrs_serialization(cls, queryset):
        return queryset.select_related('product', 'product__product_type')
