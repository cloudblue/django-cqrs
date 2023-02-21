#  Copyright © 2023 Ingram Micro Inc. All rights reserved.
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from app.models import (
    Product,
    ProductType,
    Purchase,
    User,
)


def _render_page(request, **kwargs):
    return render(request, 'main.html', {
        'users': User.objects.order_by('pk'),
        'product_types': ProductType.objects.order_by('pk'),
        'products': Product.objects.order_by('pk'),
        'purchases': Purchase.objects.order_by('pk'),
        **kwargs,
    })


def render_main_page_if_get(f):
    def wrap(request, *args, **kwargs):
        if request.method == 'GET':
            return _render_page(request)
        if request.method != 'POST':
            return HttpResponseNotAllowed(['GET', 'POST'])
        return f(request, *args, **kwargs)
    return wrap


@require_http_methods(['GET'])
def main_view(request):
    return _render_page(request)


@render_main_page_if_get
def user_create_view(request):
    username = request.POST.get('username')
    if User.objects.filter(username=username).exists():
        return _render_page(request, user_error='Username must be unique')
    User.objects.create(username=request.POST.get('username'))
    return redirect('/')


@render_main_page_if_get
def user_update_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.username += '1'
    user.save()
    return redirect('/')


@render_main_page_if_get
def user_delete_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.delete()
    return redirect('/')


@render_main_page_if_get
def product_create_view(request):
    product_type_id = request.POST.get('product_type')
    name = request.POST.get('name')
    Product.objects.create(product_type_id=product_type_id, name=name)
    return redirect('/')


@render_main_page_if_get
def product_delete_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect('/')


@render_main_page_if_get
def purchase_create_view(request):
    user_id = request.POST.get('user')
    product_id = request.POST.get('product')
    Purchase.objects.create(user_id=user_id, product_id=product_id)
    return redirect('/')


@render_main_page_if_get
def purchase_delete_view(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    purchase.delete()
    return redirect('/')
