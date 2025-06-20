#  Copyright © 2025 CloudBlue All rights reserved.

import django  # pragma: no cover


if django.VERSION < (3, 2):  # pragma: no cover
    default_app_config = 'dj_cqrs.apps.CQRSConfig'
