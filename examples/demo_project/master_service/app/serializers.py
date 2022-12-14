#  Copyright © 2021 Ingram Micro Inc. All rights reserved.
from app.models import Purchase
from rest_framework import serializers


class ProductSerializer:
    """
        Simple serializer
    """
    def __init__(self, instance):
        self.instance = instance

    @property
    def data(self):
        return {
            'id': self.instance.id,
            'name': self.instance.name,
            'product_type': {
                'id': self.instance.product_type.id,
                'name': self.instance.product_type.name,
            },
        }


class PurchaseSerializer(serializers.ModelSerializer):
    """
        Django REST Framework serializers are compatible
    """
    product_name = serializers.CharField(source='product.name')

    class Meta:
        model = Purchase
        fields = ('id', 'user_id', 'product_name', 'action_time')
