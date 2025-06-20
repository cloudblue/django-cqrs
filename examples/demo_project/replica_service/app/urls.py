#  Copyright © 2025 CloudBlue Inc. All rights reserved.
from django.urls import path

from app.views import main_page_view


urlpatterns = [
    path('', main_page_view),
]
