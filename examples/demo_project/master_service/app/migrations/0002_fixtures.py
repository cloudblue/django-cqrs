#  Copyright © 2023 Ingram Micro Inc. All rights reserved.

from django.db import migrations


def create_users(apps, schema_editor):
    User = apps.get_model('app', 'User')
    to_create = []
    for username in ('Mal', 'Zoe', 'Wash', 'Inara', 'Jayne', 'Kaylee', 'Simon', 'River'):
        to_create.append(User(username=username))
    User.objects.bulk_create(to_create)


def create_products(apps, schema_editor):
    ProductType = apps.get_model('app', 'ProductType')
    Product = apps.get_model('app', 'Product')

    products = {
        'food': ['apple', 'meat', 'banana'],
        'weapon': ['blaster', 'gun', 'knife'],
        'starships': ['Serenity'],
    }
    to_create = []
    for key, items in products.items():
        product_type = ProductType.objects.create(name=key)
        for product in items:
            to_create.append(Product(name=product, product_type=product_type))
    Product.objects.bulk_create(to_create)


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_users, migrations.RunPython.noop),
        migrations.RunPython(create_products, migrations.RunPython.noop),
    ]
