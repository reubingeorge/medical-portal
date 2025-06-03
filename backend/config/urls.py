"""
URL Configuration for the Medical Portal project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.i18n import set_language

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('set-language/', set_language, name='set_language'),

    # Include app URLs
    path('', include('apps.accounts.urls', namespace='accounts')),
    path('medical/', include('apps.medical.urls', namespace='medical')),
    path('chat/', include('apps.chat.urls', namespace='chat')),
    path('audit/', include('apps.audit.urls', namespace='audit')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)