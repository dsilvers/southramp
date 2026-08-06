import io

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image as PILImage

JPEG_EXTS = (".jpg", ".jpeg")


class InvalidImageError(ValueError):
    """Raised when an upload isn't a readable image (client sent a broken/partial file)."""


def normalize_to_jpg(file_obj, original_filename):
    """Returns (jpg_bytes, jpg_filename). Converts via Pillow if not already a JPEG.

    Always verifies the upload decodes as a real image first — a filename
    ending in .jpg is not proof the bytes behind it are valid, and a client
    that failed mid-upload shouldn't leave a corrupt file on disk.
    """
    file_obj.seek(0)
    try:
        with PILImage.open(file_obj) as im:
            im.verify()
    except Exception as exc:
        raise InvalidImageError(f"not a valid image: {exc}") from exc

    lower = original_filename.lower()
    stem = original_filename.rsplit(".", 1)[0] if "." in original_filename else original_filename

    if lower.endswith(JPEG_EXTS):
        file_obj.seek(0)
        return file_obj.read(), f"{stem}.jpg"

    file_obj.seek(0)
    with PILImage.open(file_obj) as im:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG")
        return buf.getvalue(), f"{stem}.jpg"


def save_camera_image(camera, file_obj, original_filename):
    from .models import Image

    jpg_bytes, jpg_filename = normalize_to_jpg(file_obj, original_filename)
    image = Image(camera=camera, taken_at=timezone.now())
    image.file.save(jpg_filename, ContentFile(jpg_bytes), save=True)
    generate_embed_images(image)
    return image


def generate_embed_images(image):
    """Generates one resized EmbedImage per configured width, for cameras with embedding enabled."""
    from .models import EmbedImage

    camera = image.camera
    if not camera.embed_enabled:
        return
    widths = camera.embed_widths()
    if not widths:
        return

    image.file.open("rb")
    try:
        with PILImage.open(image.file) as im:
            im = im.convert("RGB")
            original_width, original_height = im.size
            for width in widths:
                height = round(original_height * (width / original_width))
                buf = io.BytesIO()
                im.resize((width, height)).save(buf, "JPEG")
                embed = EmbedImage(image=image, width=width)
                embed.file.save(f"{width}.jpg", ContentFile(buf.getvalue()), save=True)
    finally:
        image.file.close()


def save_unrecognized_upload(secret, file_obj, original_filename, remote_addr=None):
    from .models import UnrecognizedUpload

    jpg_bytes, jpg_filename = normalize_to_jpg(file_obj, original_filename)
    upload = UnrecognizedUpload(
        secret=secret,
        original_filename=original_filename,
        remote_addr=remote_addr,
    )
    upload.file.save(jpg_filename, ContentFile(jpg_bytes), save=True)
    return upload
