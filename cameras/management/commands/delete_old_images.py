from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from cameras.models import Image


class Command(BaseCommand):
    help = "Deletes Image rows (and their files, and any resized embeds) older than N days (default 5)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=5)

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        qs = Image.objects.filter(taken_at__lt=cutoff)
        count = qs.count()

        for image in qs.prefetch_related("embeds").iterator():
            for embed in image.embeds.all():
                embed.file.delete(save=False)
            image.file.delete(save=False)

        qs.delete()
        self.stdout.write(f"Deleted {count} images (and their embeds) older than {options['days']} days")
