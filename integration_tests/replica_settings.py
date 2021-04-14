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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.getenv('POSTGRES_HOST', 'postgres'),
        'NAME': os.getenv('POSTGRES_DB', 'replica'),
        'USER': os.getenv('POSTGRES_USER', 'user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'pswd'),
    }
}

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

CQRS = {
    'transport': os.getenv('CQRS_REPLICA_TRANSPORT'),
    'url': os.getenv('CQRS_BROKER_URL'),
    'consumer_prefetch_count': 2,
    'queue': 'replica',
    'replica': {
        'CQRS_MAX_RETRIES': 2,
        'CQRS_RETRY_DELAY': 1,
        'delay_queue_max_size': 10,
        'dead_letter_queue': 'dead_letter_replica',
        'dead_message_ttl': 5,
    }
}
