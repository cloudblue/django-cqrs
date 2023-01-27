#  Copyright © 2023 Ingram Micro Inc. All rights reserved.

from django.apps import AppConfig
from django.conf import settings

from dj_cqrs._validation import validate_settings


class CQRSConfig(AppConfig):
    name = 'dj_cqrs'

    def ready(self):
        validate_settings(settings)
