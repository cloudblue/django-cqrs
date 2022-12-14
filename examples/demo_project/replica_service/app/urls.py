#  Copyright © 2021 Ingram Micro Inc. All rights reserved.
from app.views import main_page_view
from django.urls import path


urlpatterns = [
    path('', main_page_view),
]
