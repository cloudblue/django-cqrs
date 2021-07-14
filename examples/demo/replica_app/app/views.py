from django.shortcuts import render
from django.core.cache import cache
from app.models import User, Product


def main_page_view(request):
    return render(request, 'main.html', {
        'users': User.objects.order_by('pk'),
        'products': Product.objects.select_related('product_type').order_by('pk'),
        'purchases': [cache.get(key) for key in cache.keys('purchase_*')],
    })
