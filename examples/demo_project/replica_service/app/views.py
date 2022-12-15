#  Copyright © 2021 Ingram Micro Inc. All rights reserved.
from app.models import Product, User
from django.core.cache import cache
from django.shortcuts import render


def main_page_view(request):
    return render(request, 'main.html', {
        'users': User.objects.order_by('pk'),
        'products': Product.objects.select_related('product_type').order_by('pk'),
        'purchases': [cache.get(key) for key in cache.keys('purchase_*')],
    })
