from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from app.models import User, ProductType, Product, Purchase


def _render_page(request, **kwargs):
    return render(request, 'main.html', {
        'users': User.objects.order_by('pk'),
        'product_types': ProductType.objects.order_by('pk'),
        'products': Product.objects.order_by('pk'),
        'purchases': Purchase.objects.order_by('pk'),
        **kwargs,
    })


@require_http_methods(['GET'])
def main_view(request):
    return _render_page(request)


@require_http_methods(['POST'])
def user_create_view(request):
    username = request.POST.get('username')
    if User.objects.filter(username=username).exists():
        return _render_page(request, user_error='Username must be unique')
    User.objects.create(username=request.POST.get('username'))
    return redirect('/')


@require_http_methods(['POST'])
def user_update_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.username += '1'
    user.save()
    return redirect('/')


@require_http_methods(['POST'])
def user_delete_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.delete()
    return redirect('/')


@require_http_methods(['POST'])
def create_product_view(request):
    product_type_id = request.POST.get('product_type')
    name = request.POST.get('name')
    Product.objects.create(product_type_id=product_type_id, name=name)
    return redirect('/')


@require_http_methods(['POST'])
def create_purchase_view(request):
    user_id = request.POST.get('user')
    product_id = request.POST.get('product')
    Purchase.objects.create(user_id=user_id, product_id=product_id)
    return redirect('/')
