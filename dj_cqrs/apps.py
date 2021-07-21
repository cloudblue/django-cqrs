#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from dj_cqrs._validation import validate_settings

from django.apps import AppConfig
from django.conf import settings


class CQRSConfig(AppConfig):
    name = 'dj_cqrs'

    def ready(self):
        validate_settings(settings)
