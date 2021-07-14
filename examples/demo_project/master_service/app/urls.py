#  Copyright © 2021 Ingram Micro Inc. All rights reserved.
from django.urls import path

from app.views import (
    main_view,
    product_create_view, product_delete_view, purchase_create_view,
    purchase_delete_view,
    user_create_view, user_delete_view, user_update_view,
)

urlpatterns = [
    path('', main_view),
    path('users/', user_create_view),
    path('users/<int:pk>/update/', user_update_view),
    path('users/<int:pk>/delete/', user_delete_view),
    path('products/', product_create_view),
    path('products/<int:pk>/delete/', product_delete_view),
    path('purchases/', purchase_create_view),
    path('purchases/<int:pk>/delete/', purchase_delete_view),
]
