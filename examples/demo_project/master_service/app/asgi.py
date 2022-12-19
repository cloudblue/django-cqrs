#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

"""
ASGI config for master_service project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'master_service.settings')

application = get_asgi_application()
