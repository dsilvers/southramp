import uuid

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Camera, Image, Location
from .utils import InvalidImageError, save_camera_image, save_unrecognized_upload


def _is_stale(image):
    if image is None:
        return False
    cutoff = timezone.now() - timezone.timedelta(minutes=settings.CAMERA_STALE_MINUTES)
    return image.taken_at < cutoff


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def index(request):
    locations = Location.objects.filter(hidden=False).prefetch_related("cameras")
    for loc in locations:
        loc.visible_cameras = [c for c in loc.cameras.all() if not c.hidden]

    latest_public = (
        Image.objects.filter(camera__hidden=False, camera__location__hidden=False)
        .order_by("-taken_at")
        .first()
    )
    og_image_url = request.build_absolute_uri(latest_public.file.url) if latest_public else None

    return render(request, "cameras/index.html", {
        "locations": locations,
        "og_image_url": og_image_url,
    })


def location_detail(request, slug):
    # No hidden filter: a direct link to a location shows every one of its
    # cameras, hidden or not — same "unlisted, not blocked" rule as cameras.
    location = get_object_or_404(Location, slug=slug)
    cameras = location.cameras.all()

    latest_public = (
        Image.objects.filter(camera__in=cameras).order_by("-taken_at").first()
    )
    og_image_url = request.build_absolute_uri(latest_public.file.url) if latest_public else None

    return render(request, "cameras/location_detail.html", {
        "location": location,
        "cameras": cameras,
        "og_image_url": og_image_url,
    })


def _camera_detail(request, slug):
    camera = get_object_or_404(Camera, slug=slug)
    images = list(camera.images.order_by("-taken_at")[: settings.CAMERA_STRIP_INITIAL + 1])
    latest = images[0] if images else None
    strip = images[1:]

    og_image_url = request.build_absolute_uri(latest.file.url) if latest else None

    return render(request, "cameras/camera_detail.html", {
        "camera": camera,
        "latest": latest,
        "is_stale": _is_stale(latest),
        "strip": strip,
        "page_size": settings.CAMERA_STRIP_PAGE_SIZE,
        "og_image_url": og_image_url,
    })


@csrf_exempt
@require_http_methods(["GET", "POST"])
def camera_dispatch(request, identifier):
    if request.method == "GET":
        return _camera_detail(request, identifier)

    try:
        secret = uuid.UUID(identifier)
    except ValueError:
        return HttpResponseBadRequest("invalid identifier")

    uploaded = request.FILES.get("image")
    if uploaded is None:
        return HttpResponseBadRequest("missing 'image' file field")

    camera = Camera.objects.filter(secret=secret).first()
    try:
        if camera is not None:
            save_camera_image(camera, uploaded, uploaded.name)
        else:
            save_unrecognized_upload(secret, uploaded, uploaded.name, remote_addr=_client_ip(request))
    except InvalidImageError:
        # Client-side upload failure (truncated/corrupt file) — nothing
        # worth persisting or surfacing as a discovery candidate.
        pass

    return HttpResponse("OK")


def camera_images_json(request, identifier):
    camera = get_object_or_404(Camera, slug=identifier)

    try:
        before_id = int(request.GET.get("before_id", 0)) or None
    except ValueError:
        before_id = None

    qs = camera.images.order_by("-taken_at")
    if before_id:
        anchor = camera.images.filter(pk=before_id).first()
        if anchor:
            qs = qs.filter(taken_at__lt=anchor.taken_at)

    page_size = settings.CAMERA_STRIP_PAGE_SIZE
    page = list(qs[:page_size])
    has_more = camera.images.filter(taken_at__lt=page[-1].taken_at).exists() if page else False

    return JsonResponse({
        "images": [
            {
                "id": img.pk,
                "url": img.file.url,
                "taken_at": img.taken_at.isoformat(),
                "stale": _is_stale(img),
            }
            for img in page
        ],
        "has_more": has_more,
    })
