#  Copyright © 2025 CloudBlue Inc. All rights reserved.

import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'integration_tests.replica_settings')

application = get_wsgi_application()
