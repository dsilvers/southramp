import io
from urllib.parse import urlsplit, urlunsplit

import requests
from django.core.management.base import BaseCommand

from cameras.models import Camera
from cameras.utils import InvalidImageError, save_camera_image


def _resolve_url(camera):
    """Returns the URL to fetch, or None if DDNS substitution is needed but unavailable."""
    url = camera.remote_pull_url
    if not camera.remote_pull_use_location_ddns:
        return url

    ip = camera.location.last_known_ip
    if not ip:
        return None

    parts = urlsplit(url)
    netloc = f"{ip}:{parts.port}" if parts.port else ip
    if parts.username:
        userinfo = parts.username if parts.password is None else f"{parts.username}:{parts.password}"
        netloc = f"{userinfo}@{netloc}"
    return urlunsplit(parts._replace(netloc=netloc))


class Command(BaseCommand):
    help = "Pulls a snapshot from each remote-pull-enabled camera and saves it as an Image."

    def handle(self, *args, **options):
        cameras = Camera.objects.filter(remote_pull_enabled=True).select_related("location")

        for camera in cameras:
            if not camera.remote_pull_url:
                self.stderr.write(f"{camera}: remote pull enabled but no URL configured, skipping")
                continue

            url = _resolve_url(camera)
            if url is None:
                self.stderr.write(f"{camera}: DDNS substitution enabled but location has no known IP yet, skipping")
                continue

            try:
                resp = requests.get(url, timeout=camera.remote_pull_timeout)
                resp.raise_for_status()
            except requests.RequestException as exc:
                self.stderr.write(f"{camera}: fetch failed: {exc}")
                continue

            try:
                save_camera_image(camera, io.BytesIO(resp.content), f"{camera.slug}.jpg")
            except InvalidImageError as exc:
                self.stderr.write(f"{camera}: {exc}")
                continue

            self.stdout.write(f"{camera}: saved")
