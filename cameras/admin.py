from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html

from .models import Camera, Image, Location, UnrecognizedUpload


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "slug", "hidden", "camera_count", "last_known_ip")
    list_display_links = ("name",)
    list_editable = ("order",)
    list_filter = ("hidden",)
    search_fields = ("name",)
    ordering = ("order", "name")
    readonly_fields = (
        "dynamic_dns_username",
        "dynamic_dns_password",
        "dynamic_dns_endpoint",
        "last_known_ip",
        "ip_updated_at",
    )
    fieldsets = (
        (None, {"fields": ("name", "slug", "hidden", "order")}),
        ("Dynamic DNS", {
            "fields": (
                "dynamic_dns_enabled",
                "dynamic_dns_username",
                "dynamic_dns_password",
                "dynamic_dns_endpoint",
                "last_known_ip",
                "ip_updated_at",
            ),
        }),
    )

    def camera_count(self, obj):
        return obj.cameras.count()

    def dynamic_dns_endpoint(self, obj):
        return format_html("<code>{}</code>/nic/update", self._domain())

    dynamic_dns_endpoint.short_description = "Endpoint (for UniFi's \"Server\" field)"

    def _domain(self):
        return settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "<your-domain>"


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "location", "slug", "hidden", "ftp_username", "remote_pull_enabled")
    list_display_links = ("name",)
    list_editable = ("order",)
    list_filter = ("hidden", "location", "remote_pull_enabled")
    search_fields = ("name", "ftp_username")
    ordering = ("location__order", "location__name", "order", "name")
    fieldsets = (
        (None, {"fields": ("location", "name", "slug", "hidden", "order")}),
        ("Ingestion", {"fields": ("id", "secret", "ftp_username", "ftp_password")}),
        ("Remote Pull", {
            "fields": (
                "remote_pull_enabled",
                "remote_pull_use_location_ddns",
                "remote_pull_url",
                "remote_pull_timeout",
            ),
        }),
    )


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("camera", "taken_at")
    list_filter = ("camera",)


@admin.register(UnrecognizedUpload)
class UnrecognizedUploadAdmin(admin.ModelAdmin):
    list_display = ("secret", "received_at", "remote_addr", "image_preview", "create_camera_link")
    readonly_fields = ("secret", "file", "original_filename", "remote_addr", "received_at", "image_preview")

    def image_preview(self, obj):
        if not obj.file:
            return ""
        return format_html('<img src="{}" style="max-height:150px">', obj.file.url)

    def create_camera_link(self, obj):
        return format_html(
            '<a href="/southramp-admin/cameras/camera/add/?secret={}">Create camera</a>', obj.secret
        )
