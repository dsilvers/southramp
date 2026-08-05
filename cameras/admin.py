from django.contrib import admin
from django.utils.html import format_html

from .models import Camera, Image, Location, UnrecognizedUpload


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "slug", "hidden", "camera_count")
    list_display_links = ("name",)
    list_editable = ("order",)
    list_filter = ("hidden",)
    search_fields = ("name",)
    ordering = ("order", "name")

    def camera_count(self, obj):
        return obj.cameras.count()


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "location", "slug", "hidden", "ftp_username")
    list_display_links = ("name",)
    list_editable = ("order",)
    list_filter = ("hidden", "location")
    search_fields = ("name", "ftp_username")
    ordering = ("location__order", "location__name", "order", "name")
    readonly_fields = ("id",)


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
