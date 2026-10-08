from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from cameras.models import Camera, EmbedImage, Image


class Command(BaseCommand):
    help = (
        "Deletes Image rows (and their files, thumbnails, and any resized embeds) older than a given age "
        "(default 5 days), plus embeds older than --embed-hours (default 1) on any image that isn't its "
        "camera's latest."
    )

    def add_arguments(self, parser):
        parser.add_argument("--days", type=float, default=None)
        parser.add_argument("--hours", type=float, default=None)
        parser.add_argument("--embed-hours", type=float, default=1)

    def handle(self, *args, **options):
        days = options["days"]
        hours = options["hours"]
        if days is None and hours is None:
            days = 5
        if days is not None and hours is not None:
            raise CommandError("Specify only one of --days or --hours")

        age = timedelta(days=days) if days is not None else timedelta(hours=hours)
        cutoff = timezone.now() - age
        qs = Image.objects.filter(taken_at__lt=cutoff)
        count = qs.count()

        for image in qs.prefetch_related("embeds").iterator(chunk_size=200):
            for embed in image.embeds.all():
                self._delete_file(embed.file)
            self._delete_file(image.thumbnail)
            self._delete_file(image.file)

        qs.delete()

        label = f"{days} days" if days is not None else f"{hours} hours"
        self.stdout.write(f"Deleted {count} images (and their embeds) older than {label}")

        self._delete_old_embeds(options["embed_hours"])

    def _delete_old_embeds(self, embed_hours):
        # Only the latest image's embeds are ever served (see embed_redirect),
        # so older ones can go well before their parent image does.
        cutoff = timezone.now() - timedelta(hours=embed_hours)
        latest_ids = Camera.objects.annotate(
            latest_id=Subquery(
                Image.objects.filter(camera=OuterRef("pk")).order_by("-taken_at").values("pk")[:1]
            )
        ).filter(latest_id__isnull=False).values("latest_id")
        qs = EmbedImage.objects.filter(image__taken_at__lt=cutoff).exclude(image_id__in=latest_ids)
        count = qs.count()

        for embed in qs.iterator(chunk_size=200):
            self._delete_file(embed.file)

        qs.delete()

        self.stdout.write(f"Deleted {count} embeds older than {embed_hours} hours")

    def _delete_file(self, file_field):
        if not file_field:
            return
        try:
            file_field.delete(save=False)
        except FileNotFoundError:
            pass
