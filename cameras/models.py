import secrets
import string
import uuid

from django.db import models
from django.utils.text import slugify

ALPHANUMERIC = string.ascii_letters + string.digits


def generate_credential(length=12):
    return "".join(secrets.choice(ALPHANUMERIC) for _ in range(length))


class Location(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    hidden = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    dynamic_dns_enabled = models.BooleanField(default=False)
    dynamic_dns_username = models.CharField(max_length=12, unique=True, blank=True)
    dynamic_dns_password = models.CharField(max_length=12, blank=True)
    last_known_ip = models.GenericIPAddressField(null=True, blank=True)
    ip_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        if not self.dynamic_dns_username:
            self.dynamic_dns_username = self._generate_unique_dynamic_dns_username()
        if not self.dynamic_dns_password:
            self.dynamic_dns_password = generate_credential()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base = slugify(self.name)
        slug = base
        n = 1
        while Location.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            n += 1
            slug = f"{base}-{n}"
        return slug

    def _generate_unique_dynamic_dns_username(self):
        while True:
            candidate = generate_credential()
            if not Location.objects.filter(dynamic_dns_username=candidate).exists():
                return candidate

    def __str__(self):
        return self.name


class Camera(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    secret = models.UUIDField(default=uuid.uuid4)

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="cameras")
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    hidden = models.BooleanField(default=False)

    ftp_username = models.CharField(max_length=12, unique=True, blank=True)
    ftp_password = models.CharField(max_length=12, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["location__order", "location__name", "order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        if not self.ftp_username:
            self.ftp_username = self._generate_unique_ftp_username()
        if not self.ftp_password:
            self.ftp_password = generate_credential()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base = slugify(self.name)
        slug = base
        n = 1
        while Camera.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            n += 1
            slug = f"{base}-{n}"
        return slug

    def _generate_unique_ftp_username(self):
        while True:
            candidate = generate_credential()
            if not Camera.objects.filter(ftp_username=candidate).exists():
                return candidate

    @property
    def latest_image(self):
        return self.images.order_by("-taken_at").first()

    def __str__(self):
        return f"{self.location.name} / {self.name}"


def camera_image_upload_to(instance, filename):
    return f"cameras/{instance.camera_id}/{filename}"


class Image(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name="images")
    file = models.ImageField(upload_to=camera_image_upload_to)
    taken_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-taken_at"]
        indexes = [models.Index(fields=["camera", "-taken_at"])]

    def __str__(self):
        return f"{self.camera.name} @ {self.taken_at:%Y-%m-%d %H:%M}"


class UnrecognizedUpload(models.Model):
    secret = models.UUIDField(db_index=True)
    file = models.ImageField(upload_to="unrecognized/%Y/%m/%d/")
    original_filename = models.CharField(max_length=255, blank=True)
    remote_addr = models.GenericIPAddressField(null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.secret} @ {self.received_at:%Y-%m-%d %H:%M}"
