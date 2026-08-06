from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from cameras import views as cameras_views

urlpatterns = [
    path("southramp-admin/", admin.site.urls),
    # Fixed path expected by dyndns2-compatible clients (UniFi's "Custom"
    # DDNS service has no path field — it always requests /nic/update on
    # whatever host is entered as "Server").
    path("nic/update", cameras_views.ddns_update),
    path("robots.txt", cameras_views.robots_txt),
    path("", include("cameras.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
