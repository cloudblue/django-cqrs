#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = '6^1@%4#qtc+bookwp4w5k-+nbo+clm!skzdhnyl@rf&06b5tl7'

DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    'dj_cqrs',
    'tests.dj_master',
    'tests.dj_replica',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tests.dj.urls'


DB_ENGINE = os.getenv('DB', 'sqlite') or 'sqlite'

if DB_ENGINE == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': 'postgres',
            'NAME': 'django_cqrs',
            'USER': 'user',
            'PASSWORD': 'pswd',
        },
    }
elif DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'HOST': 'mysql',
            'NAME': 'django_cqrs',
            'USER': 'root',
            'PASSWORD': 'password',
        },
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        },
    }

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

CQRS = {
    'transport': 'tests.dj.transport.TransportStub',
    'queue': 'replica',
    'master': {
        'CQRS_MESSAGE_TTL': 3600,
    },
    'replica': {
        'CQRS_MAX_RETRIES': 5,
        'CQRS_RETRY_DELAY': 1,
        'delay_queue_max_size': 1000,
        'dead_letter_queue': 'dead_letter_replica',
        'dead_message_ttl': 5,
    },
}
