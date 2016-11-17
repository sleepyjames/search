"""
WSGI config for testapp project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testapp.settings")

from fix_path import fix_path
fix_path()

from django.core.wsgi import get_wsgi_application
from djangae.wsgi import DjangaeApplication

application = DjangaeApplication(get_wsgi_application())
