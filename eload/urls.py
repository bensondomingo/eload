"""eload URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

from landing.views import IndexTemplateView, TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', IndexTemplateView.as_view(), name='landing'),
    path('cphapp/', include('cphapp.urls')),
    path('accounts/', include('profiles.api.urls')),
    path('auth/', include('authentication.urls')),
    path('fcm/', include('fcm.urls')),
    path('firebase-messaging-sw.js', (TemplateView.as_view(
        template_name="firebase-messaging-sw.js",
        content_type='application/javascript', )),
        name='firebase-messaging-sw.js'),
    re_path(r"^.*$", IndexTemplateView.as_view(), name='entry-point')
]

if settings.DEBUG:
    urlpatterns.insert(0, path(
        'test-auth/', include('rest_framework.urls',
                              namespace='rest_framework')))
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
