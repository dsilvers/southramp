from django import template
from django.conf import settings
from django.utils import timezone

register = template.Library()


@register.filter
def is_stale(image):
    if image is None:
        return False
    cutoff = timezone.now() - timezone.timedelta(minutes=settings.CAMERA_STALE_MINUTES)
    return image.taken_at < cutoff
