from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.db import transaction
from django.shortcuts import render
from django.utils.html import format_html

from .models import Camera, Image, Location, UnrecognizedUpload, generate_credential


class ChangeCameraIdForm(forms.Form):
    new_id = forms.UUIDField(label="New ID")


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
    readonly_fields = ("id",)
    actions = ["change_id"]
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

    @admin.action(description="Change ID for selected camera")
    def change_id(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select exactly one camera to change its ID.", level=messages.ERROR)
            return

        camera = queryset.first()

        if "apply" in request.POST:
            form = ChangeCameraIdForm(request.POST)
            if form.is_valid():
                new_id = form.cleaned_data["new_id"]
                if Camera.objects.filter(pk=new_id).exists():
                    form.add_error("new_id", "A camera with this ID already exists.")
                else:
                    self._rename_camera_id(camera, new_id)
                    self.message_user(request, f"Changed {camera.name}'s ID to {new_id}.")
                    return
        else:
            form = ChangeCameraIdForm(initial={"new_id": camera.pk})

        return render(request, "admin/cameras/camera/change_id.html", {
            "camera": camera,
            "form": form,
            "opts": self.model._meta,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        })

    @staticmethod
    def _rename_camera_id(camera, new_id):
        # Django decides INSERT vs UPDATE by primary key value, so a plain
        # save() with a new id would create a second row rather than
        # renaming this one. Instead: create the new row, re-point its
        # Images, then delete the old row — all as one transaction. The old
        # row's slug/ftp_username are freed to a placeholder first since
        # both are unique and the new row needs the real values before the
        # old row goes away.
        with transaction.atomic():
            placeholder = generate_credential()
            Camera.objects.filter(pk=camera.pk).update(
                ftp_username=placeholder, slug=f"migrating-{placeholder}"
            )
            new_camera = Camera.objects.create(
                id=new_id,
                secret=camera.secret,
                location=camera.location,
                name=camera.name,
                slug=camera.slug,
                hidden=camera.hidden,
                ftp_username=camera.ftp_username,
                ftp_password=camera.ftp_password,
                order=camera.order,
                remote_pull_enabled=camera.remote_pull_enabled,
                remote_pull_use_location_ddns=camera.remote_pull_use_location_ddns,
                remote_pull_url=camera.remote_pull_url,
                remote_pull_timeout=camera.remote_pull_timeout,
            )
            Image.objects.filter(camera_id=camera.pk).update(camera=new_camera)
            Camera.objects.filter(pk=camera.pk).delete()


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
