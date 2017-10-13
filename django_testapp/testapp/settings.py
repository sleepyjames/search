"""
Django settings for testapp project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""
import sys
import django
from djangae.settings_base import *

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '&x$ts1u)tx#5zsi84555$(@mydbz06&q23p8=c6fs1!d4%1a^u'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'djangae',
    'django.contrib.admin',
    'django.contrib.auth',
    'djangae.contrib.gauth.datastore',
    'djangae.contrib.security',
    'djangae.contrib.consistency',
    'django.contrib.contenttypes',
    'djangae.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'djangae.contrib.locking',
    'djangae.contrib.mappers',
    'djangae.contrib.pagination',
    'djangae.contrib.uniquetool',
    'testapp',
    'search.django',
]


MIDDLEWARE_CLASSES = (
    'djangae.contrib.security.middleware.AppEngineSecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'djangae.contrib.gauth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'testapp.urls'
SITE_ID = 1
WSGI_APPLICATION = 'testapp.wsgi.application'


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'djangae.db.backends.appengine',
        'NAMESPACE': 'customdefaultnamespace',
    },
    "ns1": {
        'ENGINE': 'djangae.db.backends.appengine',
        'NAMESPACE': 'ns1namespace',
    },
    "nonamespace": {
        'ENGINE': 'djangae.db.backends.appengine',
    },
}

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_ROOT = BASE_DIR + 'static'
STATIC_URL = '/static/'

AUTH_USER_MODEL = 'djangae.GaeDatastoreUser'
GENERATE_SPECIAL_INDEXES_DURING_TESTING = True
COMPLETE_FLUSH_WHILE_TESTING = True
DJANGAE_SEQUENTIAL_IDS_IN_TESTS = True

TEST_RUNNER = 'djangae.test_runner.SkipUnsupportedRunner'


# Here because of "You haven't defined a TEMPLATES setting" deprecation message
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
    },
]

from djangae.contrib.gauth.settings import *
