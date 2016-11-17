import sys
from django.conf.urls import include, url

from django.contrib import admin
admin.autodiscover()

import djangae.urls


def do_something():
    return


def view_that_defers(request):
    from google.appengine.ext.deferred import defer
    from django.http import HttpResponse

    defer(do_something)

    return HttpResponse("OK")

urlpatterns = [
    # Examples:
    # url(r'^$', 'testapp.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^_ah/', include(djangae.urls)),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^auth/', include('djangae.contrib.gauth.urls')),
    url(r'^$', view_that_defers),
]
