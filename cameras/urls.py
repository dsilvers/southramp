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
    # Matches the old app's embed URL exactly, including the lack of a
    # trailing slash — third-party pages already embed this shape.
    path("embed/<uuid:camera_id>/<int:width>", views.embed_redirect, name="embed_redirect"),
    # Another legacy URL, same behavior as /embed/. The trailing integer is
    # part of the old app's URL shape but unused here (no per-request aspect
    # ratio/height variants — width is the only thing embeds are generated at).
    path("thumb/<uuid:camera_id>/<int:width>/<int:ignored>", views.embed_redirect, name="thumb_redirect"),
    path("<slug:location_slug>/<slug:camera_slug>/images/", views.camera_images_json, name="camera_images_json"),
    path("<slug:location_slug>/<slug:camera_slug>/", views.camera_detail, name="camera_detail"),
    # Kept last: a bare "<slug>/" is the most generic pattern here, so it
    # must not shadow the more specific routes above it.
    path("<slug:slug>/", views.location_detail, name="location_detail"),
]
