from django.urls import path

from . import views

app_name = "cameras"

urlpatterns = [
    path("", views.index, name="index"),
    # No-slash variant kept alongside the canonical one: legacy cameras POST
    # to /camera/<secret> with no trailing slash, and Django's APPEND_SLASH
    # redirect turns a 301-redirected POST into a GET, dropping the upload.
    path("camera/<str:identifier>", views.camera_dispatch),
    path("camera/<str:identifier>/", views.camera_dispatch, name="camera_dispatch"),
    path("camera/<str:identifier>/images/", views.camera_images_json, name="camera_images_json"),
    # Kept last: a bare "<slug>/" is the most generic pattern here, so it
    # must not shadow the more specific "camera/..." routes above it.
    path("<slug:slug>/", views.location_detail, name="location_detail"),
]
