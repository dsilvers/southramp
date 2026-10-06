from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from cameras.models import Image
from cameras.utils import make_thumbnail


class Command(BaseCommand):
    help = "Generates thumbnails for Image rows that don't have one yet. Safe to re-run."

    def handle(self, *args, **options):
        qs = Image.objects.filter(thumbnail="").order_by("-taken_at")
        total = qs.count()
        done = failed = 0

        for image in qs.iterator(chunk_size=200):
            try:
                with image.file.open("rb") as fh:
                    jpg_bytes = fh.read()
                stem = image.file.name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                image.thumbnail.save(f"{stem}_thumb.jpg", ContentFile(make_thumbnail(jpg_bytes)), save=False)
                image.save(update_fields=["thumbnail"])
                done += 1
            except Exception as exc:
                failed += 1
                self.stderr.write(f"Image {image.pk}: {exc}")

            if (done + failed) % 100 == 0:
                self.stdout.write(f"{done + failed}/{total}")

        self.stdout.write(f"Generated {done} thumbnails ({failed} failed) of {total} missing")
