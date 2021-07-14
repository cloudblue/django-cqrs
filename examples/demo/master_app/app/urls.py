from django.urls import path
from app.views import (
    main_view, user_create_view, user_update_view, user_delete_view, create_purchase_view,
    create_product_view,
)

urlpatterns = [
    path('', main_view),
    path('users/', user_create_view),
    path('users/<int:pk>/update/', user_update_view),
    path('users/<int:pk>/delete/', user_delete_view),
    path('products/', create_product_view),
    path('purchases/', create_purchase_view),
]
