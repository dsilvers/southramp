from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from cameras.models import Image


class Command(BaseCommand):
    help = "Deletes Image rows (and their files, and any resized embeds) older than a given age (default 5 days)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=float, default=None)
        parser.add_argument("--hours", type=float, default=None)

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

        for image in qs.prefetch_related("embeds").iterator():
            for embed in image.embeds.all():
                self._delete_file(embed.file)
            self._delete_file(image.file)

        qs.delete()

        label = f"{days} days" if days is not None else f"{hours} hours"
        self.stdout.write(f"Deleted {count} images (and their embeds) older than {label}")

    def _delete_file(self, file_field):
        if not file_field:
            return
        try:
            file_field.delete(save=False)
        except FileNotFoundError:
            pass
